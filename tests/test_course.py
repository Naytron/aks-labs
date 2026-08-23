import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CourseStructureTests(unittest.TestCase):
    def test_all_course_days_exist(self) -> None:
        expected = {
            "00-prework",
            "01-foundations",
            "02-architecture",
            "03-security-delivery",
            "04-operations",
            "05-capstone",
            "06-arc-runners",
        }
        actual = {path.name for path in (ROOT / "labs").iterdir() if path.is_dir()}
        self.assertEqual(actual, expected)

    def test_each_lab_follows_challenge_contract(self) -> None:
        headings = {
            "## Before you begin",
            "## Outcome",
            "## Must-know facts",
            "## Challenge",
            "## Checkpoints",
            "## Acceptance criteria",
            "## Break/fix",
            "## Hints",
            "## Tips and production notes",
            "## Cleanup",
            "## Daily gate",
        }
        for readme in sorted((ROOT / "labs").glob("*/README.md")):
            content = readme.read_text(encoding="utf-8")
            missing = headings.difference(content.splitlines())
            self.assertFalse(missing, f"{readme.relative_to(ROOT)} missing {sorted(missing)}")
            self.assertGreater(len(content.split()), 300, f"{readme.relative_to(ROOT)} is too shallow")

    def test_staged_azure_overlays_exist(self) -> None:
        for stage in ("day2", "day3", "day4"):
            path = ROOT / "platform" / "environments" / f"azure-{stage}" / "kustomization.yaml"
            self.assertTrue(path.is_file(), f"Missing {path.relative_to(ROOT)}")

    def test_documented_scripts_exist(self) -> None:
        pattern = re.compile(r"(?:\./)?scripts/([A-Za-z0-9.-]+\.ps1)")
        failures: list[str] = []
        for markdown in ROOT.rglob("*.md"):
            if ".git" in markdown.parts:
                continue
            for script in pattern.findall(markdown.read_text(encoding="utf-8")):
                if not (ROOT / "scripts" / script).is_file():
                    failures.append(f"{markdown.relative_to(ROOT)} -> scripts/{script}")
        self.assertFalse(failures, "Missing documented scripts:\n" + "\n".join(failures))

    def test_learner_docs_use_staged_azure_paths(self) -> None:
        failures: list[str] = []
        for folder in ("labs", "solutions"):
            for markdown in (ROOT / folder).rglob("*.md"):
                content = markdown.read_text(encoding="utf-8")
                if "platform/environments/azure`" in content or "platform/environments/azure-identity" in content:
                    failures.append(str(markdown.relative_to(ROOT)))
        self.assertFalse(failures, f"Legacy Azure overlay paths remain in {failures}")

    def test_local_markdown_links_resolve(self) -> None:
        link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
        failures: list[str] = []
        for markdown in ROOT.rglob("*.md"):
            if ".git" in markdown.parts:
                continue
            for target in link_pattern.findall(markdown.read_text(encoding="utf-8")):
                clean_target = target.split("#", 1)[0]
                if not clean_target or re.match(r"^(https?|mailto):", clean_target):
                    continue
                resolved = (markdown.parent / clean_target).resolve()
                if not resolved.exists():
                    failures.append(f"{markdown.relative_to(ROOT)} -> {target}")
        self.assertFalse(failures, "Broken local links:\n" + "\n".join(failures))

    def test_dockerfiles_have_required_hardening(self) -> None:
        for dockerfile in (ROOT / "app").glob("*/Dockerfile"):
            content = dockerfile.read_text(encoding="utf-8")
            self.assertRegex(content, r"(?m)^USER 10001:10001$")
            self.assertIn("HEALTHCHECK", content)
            self.assertNotRegex(content, r"(?m)^FROM .+:latest$")
            self.assertNotIn("COPY . .", content)

    def test_yaml_contains_no_patch_transcript(self) -> None:
        failures: list[str] = []
        for yaml_file in list(ROOT.rglob("*.yaml")) + list(ROOT.rglob("*.yml")):
            content = yaml_file.read_text(encoding="utf-8")
            if "*** Update File:" in content or re.search(r"(?m)^\+?@@$", content):
                failures.append(str(yaml_file.relative_to(ROOT)))
        self.assertFalse(failures, f"Patch transcript found in YAML: {failures}")

    def test_no_learner_secret_literals(self) -> None:
        patterns = [
            re.compile(r"AKIA[0-9A-Z]{16}"),
            re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
            re.compile(r"(?i)clientSecret\s*[:=]\s*[\"'][^\"']+"),
        ]
        failures: list[str] = []
        for path in ROOT.rglob("*"):
            if not path.is_file() or ".git" in path.parts or path.suffix in {".png", ".jpg", ".gif"}:
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for pattern in patterns:
                if pattern.search(content):
                    failures.append(str(path.relative_to(ROOT)))
        self.assertFalse(failures, f"Potential secrets found in {failures}")

    def test_arc_extension_has_complete_assets(self) -> None:
        expected = (
            "labs/06-arc-runners/README.md",
            "labs/06-arc-runners/arc-decision-record.md",
            "labs/06-arc-runners/arc-evidence.md",
            "labs/06-arc-runners/templates/arc-scale-test.yml",
            "solutions/arc-runners.md",
            "coach/arc-runners.md",
            "docs/instructor-arc-setup.md",
            "docs/cheatsheets/arc-runner-operations.md",
            "infra/standard/arc-runner-pool.bicep",
            "platform/arc/controller-values.yaml",
            "platform/arc/runner-scale-set-values.yaml",
            "platform/arc/versions.json",
        )
        for relative_path in expected:
            self.assertTrue((ROOT / relative_path).is_file(), relative_path)

    def test_arc_workflow_template_is_manual_and_unprivileged(self) -> None:
        workflow = (
            ROOT / "labs" / "06-arc-runners" / "templates" / "arc-scale-test.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch", workflow)
        self.assertIn("permissions: {}", workflow)
        self.assertIn("runs-on: arc-aks-lab", workflow)
        self.assertIn("timeout-minutes:", workflow)
        self.assertNotRegex(
            workflow,
            r"(?m)^\s*(pull_request|pull_request_target|push|schedule|workflow_call):",
        )
        self.assertNotIn("uses:", workflow)
        for forbidden in ("docker.sock", "privileged", "kubeconfig", "cluster-admin"):
            self.assertNotIn(forbidden, workflow.lower())
        self.assertFalse(
            (ROOT / ".github" / "workflows" / "arc-scale-test.yml").exists()
        )

    def test_arc_dependencies_and_images_are_immutable(self) -> None:
        versions = json.loads(
            (ROOT / "platform" / "arc" / "versions.json").read_text(encoding="utf-8")
        )
        self.assertEqual(versions["helmMajorVersion"], 3)
        self.assertRegex(versions["helmVersion"], r"^3\.\d+\.\d+$")
        self.assertEqual(
            versions["controllerChartVersion"],
            versions["runnerScaleSetChartVersion"],
        )
        self.assertRegex(versions["controllerChartVersion"], r"^\d+\.\d+\.\d+$")
        for key in ("controllerChartDigest", "runnerScaleSetChartDigest"):
            self.assertRegex(versions[key], r"^sha256:[a-f0-9]{64}$")
        for key in ("controllerImage", "runnerImage"):
            self.assertRegex(versions[key], r"^[^@\s]+@sha256:[a-f0-9]{64}$")

        values = "\n".join(
            (ROOT / "platform" / "arc" / filename).read_text(encoding="utf-8")
            for filename in ("controller-values.yaml", "runner-scale-set-values.yaml")
        )
        self.assertNotIn(":latest", values)
        self.assertIn(versions["runnerImage"], values)
        controller_match = re.fullmatch(
            r"(.+):([^@]+)@(sha256:[a-f0-9]{64})", versions["controllerImage"]
        )
        self.assertIsNotNone(controller_match)
        controller_repository, controller_tag, controller_digest = (
            controller_match.groups()
        )
        self.assertIn(f"repository: {controller_repository}", values)
        self.assertIn(f"tag: {controller_tag}@{controller_digest}", values)

    def test_arc_node_pool_and_repository_guards_are_bounded(self) -> None:
        bicep = (ROOT / "infra" / "standard" / "arc-runner-pool.bicep").read_text(
            encoding="utf-8"
        )
        for token in (
            "minCount: 0",
            "maxCount: maxCount",
            "mode: 'User'",
            "'workload=github-runner:NoSchedule'",
            "workload: 'github-runner'",
            "scaleSetPriority: 'Regular'",
        ):
            self.assertIn(token, bicep)

        helper = (ROOT / "scripts" / "arc-common.ps1").read_text(encoding="utf-8")
        deploy = (ROOT / "scripts" / "deploy-arc.ps1").read_text(encoding="utf-8")
        self.assertIn("naytron/aks-labs", helper.lower())
        self.assertIn("visibility", helper)
        self.assertIn("PRIVATE", helper)
        for key in (
            "github_app_id",
            "github_app_installation_id",
            "github_app_private_key",
        ):
            self.assertIn(key, deploy)
        self.assertNotIn("github_app_private_key:", deploy)

    def test_github_pages_site_contract(self) -> None:
        expected = (
            "docs/_config.yml",
            "docs/index.md",
            "docs/interview-questions/index.md",
            "docs/interview-questions/level-100.md",
            "docs/interview-questions/level-200.md",
            "docs/interview-questions/level-300.md",
            "docs/interview-questions/level-400.md",
        )
        for relative_path in expected:
            self.assertTrue((ROOT / relative_path).is_file(), relative_path)

        config = (ROOT / "docs" / "_config.yml").read_text(encoding="utf-8")
        self.assertIn("theme: minima", config)
        self.assertIn("url: https://naytron.github.io", config)
        self.assertIn("baseurl: /aks-labs", config)

        landing = (ROOT / "docs" / "index.md").read_text(encoding="utf-8")
        self.assertIn("permalink: /", landing)
        self.assertIn("/interview-questions/", landing)
        self.assertIn("https://github.com/Naytron/aks-labs", landing)

        expected_permalinks = {
            "index.md": "/interview-questions/",
            "level-100.md": "/interview-questions/level-100/",
            "level-200.md": "/interview-questions/level-200/",
            "level-300.md": "/interview-questions/level-300/",
            "level-400.md": "/interview-questions/level-400/",
        }
        actual_permalinks: list[str] = []
        bank = ROOT / "docs" / "interview-questions"
        for filename, permalink in expected_permalinks.items():
            content = (bank / filename).read_text(encoding="utf-8")
            match = re.search(r"(?m)^permalink:\s+(\S+)$", content)
            self.assertIsNotNone(match, filename)
            self.assertEqual(match.group(1), permalink, filename)
            actual_permalinks.append(match.group(1))
        self.assertEqual(len(actual_permalinks), len(set(actual_permalinks)))

        bank_index = (bank / "index.md").read_text(encoding="utf-8")
        for audience in (
            "Cloud Engineer",
            "DevOps Engineer",
            "Site Reliability Engineer",
            "Platform Engineer",
        ):
            self.assertIn(audience, bank_index)
        self.assertIn("question-only resource", bank_index)

    def test_question_bank_level_contracts(self) -> None:
        question_pattern = re.compile(
            r"(?m)^(\d+)\.\s+(.+\(Tests: [^)]+\))\s*$"
        )
        required_topics = {
            "level-100.md": (
                "control plane",
                "node pool",
                "service",
                "ingress",
                "azure cni",
                "persistentvolume",
                "microsoft entra",
                "rbac",
                "secret",
                "hpa",
                "cluster autoscaler",
            ),
            "level-200.md": (
                "node image",
                "azure cni overlay",
                "kubenet",
                "networkpolicy",
                "gateway api",
                "ingress-nginx",
                "private cluster",
                "csi",
                "workload identity",
                "pod identity",
                "vpa",
                "keda",
                "prometheus",
                "grafana",
                "flux",
                "argo cd",
                "github actions",
                "azure devops",
                "cost",
            ),
            "level-300.md": (
                "maintenance window",
                "maxsurge",
                "pdb",
                "topology spread",
                "multi-tenancy",
                "workload identity",
                "key vault",
                "cilium",
                "slo",
                "cluster autoscaler",
                "defender",
                "deployment safeguards",
            ),
            "level-400.md": (
                "aks automatic",
                "aks standard",
                "fleet",
                "multi-region",
                "rto",
                "rpo",
                "restore validation",
                "finops",
                "arc",
                "zero trust",
                "kubenet",
                "azure cni overlay",
                "hundreds of clusters",
            ),
        }

        bank = ROOT / "docs" / "interview-questions"
        for filename, topics in required_topics.items():
            content = (bank / filename).read_text(encoding="utf-8")
            lowered = content.lower()
            self.assertTrue(content.startswith("---"), filename)
            self.assertIn("layout: page", content, filename)
            self.assertIn("permalink: /interview-questions/", content, filename)

            questions = question_pattern.findall(content)
            self.assertEqual(len(questions), 18, filename)
            self.assertEqual(
                [int(number) for number, _ in questions],
                list(range(1, 19)),
                filename,
            )
            self.assertEqual(len(re.findall(r"\(Tests: [^)]+\)", content)), 18)

            self.assertIn("## Production situations", content, filename)
            production = content.split("## Production situations", 1)[1]
            production_questions = question_pattern.findall(production)
            self.assertEqual(
                [int(number) for number, _ in production_questions],
                [16, 17, 18],
                filename,
            )
            for _, question in production_questions:
                self.assertTrue(
                    question.startswith("**What would you do if**"),
                    f"{filename}: {question}",
                )

            for topic in topics:
                self.assertIn(topic, lowered, f"{filename} missing {topic}")
            for forbidden in ("## answers", "## answer key", "suggested answer"):
                self.assertNotIn(forbidden, lowered, filename)

    def test_question_bank_frames_legacy_technologies_as_migrations(self) -> None:
        bank = ROOT / "docs" / "interview-questions"
        level_200 = (bank / "level-200.md").read_text(encoding="utf-8").lower()
        content = level_200 + "\n" + (
            bank / "level-400.md"
        ).read_text(encoding="utf-8").lower()
        self.assertRegex(
            content,
            r"(?:legacy|migrat)[^\n]*kubenet|kubenet[^\n]*(?:legacy|migrat)",
        )
        self.assertRegex(
            level_200,
            r"(?:retired|unsupported|migrat)[^\n]*pod identity|pod identity[^\n]*(?:retired|unsupported|migrat)",
        )
        self.assertRegex(
            level_200,
            r"(?:retir|migrat)[^\n]*ingress-nginx|ingress-nginx[^\n]*(?:retir|migrat)",
        )


if __name__ == "__main__":
    unittest.main()
