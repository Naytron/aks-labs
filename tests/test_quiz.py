import json
import re
import unittest
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
QUESTION_PATTERN = re.compile(
    r"(?m)^\d+\.\s+(.+?)\s+\(Tests: ([^)]+)\)\s*$"
)


def normalize_question(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("**", "")).strip()


class QuizContentTests(unittest.TestCase):
    def test_answer_guides_match_every_source_question(self) -> None:
        all_ids: set[str] = set()

        for level in (100, 200, 300, 400):
            source_path = (
                ROOT / "docs" / "interview-questions" / f"level-{level}.md"
            )
            data_path = ROOT / "docs" / "_data" / "quiz" / f"level_{level}.json"
            source = source_path.read_text(encoding="utf-8")
            data = json.loads(data_path.read_text(encoding="utf-8"))
            source_questions = QUESTION_PATTERN.findall(source)

            self.assertEqual(data["level"], level)
            self.assertEqual(len(source_questions), 18)
            self.assertEqual(len(data["questions"]), 18)

            for index, (entry, (question, topic)) in enumerate(
                zip(data["questions"], source_questions, strict=True),
                start=1,
            ):
                expected_id = f"L{level}-Q{index:02d}"
                self.assertEqual(entry["id"], expected_id)
                self.assertNotIn(entry["id"], all_ids)
                all_ids.add(entry["id"])
                self.assertEqual(
                    normalize_question(entry["question"]),
                    normalize_question(question),
                    expected_id,
                )
                self.assertEqual(entry["topic"], topic, expected_id)
                self.assertGreaterEqual(len(entry["answer"]), 100, expected_id)
                self.assertNotRegex(
                    entry["answer"],
                    r"(?i)\b(todo|tbd|placeholder|insert answer)\b",
                    expected_id,
                )
                self.assertGreaterEqual(len(entry["learnMore"]), 1, expected_id)
                self.assertLessEqual(len(entry["learnMore"]), 2, expected_id)

                for resource in entry["learnMore"]:
                    parsed = urlparse(resource["url"])
                    self.assertEqual(parsed.scheme, "https", expected_id)
                    self.assertEqual(parsed.hostname, "learn.microsoft.com", expected_id)
                    self.assertFalse(parsed.path.startswith("/answers/"), expected_id)
                    self.assertTrue(resource["title"].strip(), expected_id)

        self.assertEqual(len(all_ids), 72)

    def test_quiz_html_has_accessible_dark_theme_and_embedded_data(self) -> None:
        path = ROOT / "docs" / "interview-questions" / "quiz.html"
        content = path.read_text(encoding="utf-8")

        for token in (
            'permalink: /interview-questions/quiz/',
            '<html lang="en" data-theme="dark">',
            'new URLSearchParams(window.location.search).get("scoutTheme")',
            'document.documentElement.setAttribute("data-theme", theme)',
            'document.documentElement.setAttribute("data-theme", "dark")',
            "--cp-bg: #f7f4ef;",
            "--cp-accent: #b11f4b;",
            'html[data-theme="dark"]',
            "--cp-bg: #3d3b3a;",
            '"Segoe UI", Aptos, Calibri',
            'aria-live="polite"',
            'role="progressbar"',
            'id="reveal-button"',
            'id="answer-panel"',
            'id="known-button"',
            'id="review-button"',
            ".button[hidden]",
            "site.data.quiz.level_100",
            "site.data.quiz.level_200",
            "site.data.quiz.level_300",
            "site.data.quiz.level_400",
        ):
            self.assertIn(token, content)

        self.assertNotIn("innerHTML", content)
        self.assertNotRegex(content, r"\son[a-z]+=")
        self.assertNotIn("<script src=", content)
        self.assertNotIn("<link ", content)
        self.assertNotIn("localStorage", content)
        self.assertNotIn("sessionStorage", content)

        scripts = re.findall(r"<script>([\s\S]*?)</script>", content)
        self.assertGreaterEqual(len(scripts), 3)
        self.assertIn('get("scoutTheme")', scripts[0])
        self.assertIn('setAttribute("data-theme", theme)', scripts[0])

        style = re.search(r"<style>([\s\S]*?)</style>", content)
        self.assertIsNotNone(style)
        non_variable_css = "\n".join(
            line for line in style.group(1).splitlines() if "--cp-" not in line
        )
        self.assertNotRegex(non_variable_css, r"#[0-9a-fA-F]{3,8}\b")
        self.assertNotRegex(non_variable_css, r"\b(?:rgb|rgba|hsl|hsla)\(")

    def test_known_answer_safety_contracts(self) -> None:
        data = {}
        for level in (100, 200, 300, 400):
            quiz = json.loads(
                (
                    ROOT / "docs" / "_data" / "quiz" / f"level_{level}.json"
                ).read_text(encoding="utf-8")
            )
            data.update({entry["id"]: entry for entry in quiz["questions"]})

        self.assertIn("initial node pool is a System pool", data["L100-Q04"]["answer"])
        self.assertIn("nondelegated subnet", data["L200-Q07"]["answer"])
        self.assertIn("separate /28-or-larger", data["L200-Q07"]["answer"])
        self.assertIn("control-plane actions", data["L300-Q06"]["answer"])
        self.assertIn(
            "container-network-observability-logs",
            " ".join(item["url"] for item in data["L300-Q08"]["learnMore"]),
        )
        self.assertIn("PDBs govern eviction, not scheduling", data["L300-Q17"]["answer"])

    def test_pages_navigation_promotes_interactive_quiz(self) -> None:
        expected_links = (
            (
                ROOT / "README.md",
                "https://naytron.github.io/aks-labs/interview-questions/quiz/",
            ),
            (
                ROOT / "docs" / "index.md",
                "'/interview-questions/quiz/' | relative_url",
            ),
            (
                ROOT / "docs" / "interview-questions" / "index.md",
                "'/interview-questions/quiz/' | relative_url",
            ),
        )
        for path, link in expected_links:
            self.assertIn(link, path.read_text(encoding="utf-8"), str(path))

        for level in (100, 200, 300, 400):
            content = (
                ROOT / "docs" / "interview-questions" / f"level-{level}.md"
            ).read_text(encoding="utf-8")
            self.assertIn(
                f"'/interview-questions/quiz/?level={level}' | relative_url",
                content,
            )


if __name__ == "__main__":
    unittest.main()
