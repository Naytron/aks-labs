import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class E2EContractTests(unittest.TestCase):
    def test_harness_exposes_required_safety_switches(self) -> None:
        content = (ROOT / "scripts" / "test-e2e.ps1").read_text(encoding="utf-8")
        for token in (
            "[CmdletBinding(SupportsShouldProcess)]",
            "[switch]$LocalOnly",
            "[switch]$LiveAzure",
            "[switch]$AcknowledgeAzureCharges",
            "$MaxBudgetUsd",
            "$KeepResourcesOnFailure",
            "[switch]$SkipLocal",
        ):
            self.assertIn(token, content)
        self.assertRegex(content, r"ValidateRange\(20,\s*50\)")

    def test_result_model_has_four_explicit_states(self) -> None:
        content = (ROOT / "scripts" / "e2e" / "common.ps1").read_text(encoding="utf-8")
        for state in ("PASS", "FAIL", "BLOCKED", "SKIPPED"):
            self.assertIn(state, content)
        self.assertIn("durationSeconds", content)
        self.assertIn("Redact-E2EFile", content)
        self.assertIn("<guid-redacted>", content)
        self.assertIn("Get-ChildItem -Path $script:E2EArtifactDirectory -Recurse -File", content)

    def test_live_path_has_final_cleanup(self) -> None:
        content = (ROOT / "scripts" / "test-e2e.ps1").read_text(encoding="utf-8")
        self.assertIn("finally", content)
        self.assertIn("'Automatic', 'Final'", content)
        self.assertIn("aks-course=level400", content)
        self.assertIn("KeepResourcesOnFailure", content)
        self.assertIn("Remove-E2EGeneratedState", content)

    def test_local_helpers_exist(self) -> None:
        for filename in ("test-compose.ps1", "test-kind.ps1", "test-azure-nowrite.ps1"):
            self.assertTrue((ROOT / "scripts" / "e2e" / filename).is_file())

    def test_manual_rehearsal_artifacts_exist(self) -> None:
        for filename in (
            "e2e-attendee-rehearsal.md",
            "e2e-observation-sheet.md",
            "e2e-test-report-template.md",
        ):
            self.assertTrue((ROOT / "docs" / filename).is_file())

    def test_no_paid_e2e_on_pull_request(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "e2e-smoke.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch", workflow)
        self.assertNotIn("pull_request:", workflow)
        self.assertIn("-LocalOnly", workflow)
        self.assertNotIn("-LiveAzure", workflow)

    def test_documented_harness_commands_exist(self) -> None:
        docs = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (ROOT / "docs").glob("e2e-*.md")
        )
        for script in re.findall(r"(?:\./)?scripts/([A-Za-z0-9.-]+\.ps1)", docs):
            self.assertTrue((ROOT / "scripts" / script).is_file(), script)


if __name__ == "__main__":
    unittest.main()
