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


if __name__ == "__main__":
    unittest.main()
