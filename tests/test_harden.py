"""Static instruction-contract checks, not a model-behavior evaluation."""
from pathlib import Path
import unittest


SKILL = Path(__file__).resolve().parents[1] / 'skills' / 'harden' / 'SKILL.md'


class HardenInstructionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = ' '.join(SKILL.read_text(encoding='utf-8').split())

    def test_bare_command_checks_context_then_git_before_asking(self):
        start = self.text.index('- Bare `/harden`:')
        end = self.text.index('- `/harden changes`:', start)
        default = self.text[start:end]
        context = default.index('1. Look back through the conversation')
        git = default.index('2. Otherwise, use read-only tools to inspect git status')
        ask = default.index('3. Ask one short question')
        self.assertLess(context, git)
        self.assertLess(git, ask)
        self.assertIn('staged, unstaged, or non-ignored untracked', default)
        self.assertIn('do not claim the tree is clean without checking', default)
        self.assertIn('not that the user forgot to supply a subject', self.text)

    def test_explicit_target_wins_and_report_follows_resolved_subject(self):
        self.assertIn('The explicit target always wins over the defaults', self.text)
        self.assertIn('Name the selected subject at the start of the report', self.text)
        self.assertIn('A bare `/harden` that falls back to git uses the diff report', self.text)
        self.assertNotIn('For a plan (bare `/harden`', self.text)

    def test_review_is_read_only_until_the_user_explicitly_authorizes_implementation(self):
        self.assertIn('Read-only review is the default for every invocation', self.text)
        self.assertIn('Selecting a subject never authorizes implementation', self.text)
        self.assertIn('Do not edit, create, move, or delete project files', self.text)
        self.assertIn('Only an explicit request to implement or fix the findings authorizes edits', self.text)
        self.assertIn('report the findings and stop', self.text)
        self.assertIn('present the improved plan in the response only', self.text)
        self.assertIn('In a normal read-only run there is no "Applied fixes" section', self.text)
        for instruction in [
            'fix it in the plan or the change',
            'Fix each one with a specific change',
            'Ablate: cut abstractions',
            'fix in this change unless accepted',
        ]:
            self.assertNotIn(instruction, self.text)

    def test_report_centers_confirmed_loopholes_and_ends_with_required_changes(self):
        template = self.text.split('~~~markdown ', 1)[1].split('~~~', 1)[0]
        self.assertIn('## Confirmed loopholes (confirmed; not modified)', template)
        self.assertIn('Evidence:', template)
        self.assertTrue(template.index('## Confirmed loopholes') < template.index('## Pending decisions'))
        final = template.rsplit('## ', 1)[1]
        self.assertTrue(final.startswith('Implementation adjustments (proposed; not applied)'))
        self.assertIn('L1 `path::symbol`', final)
        self.assertIn('verify:', final)
        self.assertIn('always include "Confirmed loopholes"', self.text)
        self.assertIn('even if both say "None"', self.text)
        self.assertIn('Confirmed does not mean fixed', self.text)
        self.assertIn('已确认的漏洞（未修改）', self.text)
        self.assertIn('需要修改的内容（建议，未执行）', self.text)
        self.assertNotIn('## Your call', template)
        self.assertNotIn('## Already handled', template)

    def test_unchecked_leads_stay_out_of_the_report_without_hiding_material_blockers(self):
        self.assertNotIn('## Unverified', self.text)
        self.assertNotIn('- U1', self.text)
        self.assertIn('Investigate assumptions before drawing conclusions', self.text)
        self.assertIn('leave unsupported suspicions out of the report', self.text)
        self.assertIn('Do not add a separate speculation or pending-validation section', self.text)
        self.assertIn('materially limits the conclusion, state that briefly in the verdict', self.text)
        self.assertIn('instead of claiming the subject is sound', self.text)

    def test_confirmed_failures_cannot_be_hidden_as_choices_or_accepted_without_consent(self):
        self.assertIn('Never report P1 0 while describing an unresolved P1 elsewhere', self.text)
        self.assertIn('"Accepted risks" contains only risks the user has actually accepted', self.text)
        self.assertIn('confirmed failure under its L ID', self.text)
        self.assertIn('an explicitly requested product or compatibility change is not itself a loophole', self.text)
        self.assertIn('Name the requirement or invariant violated', self.text)

    def test_clarifications_do_not_inherit_the_skills_english(self):
        self.assertIn('progress messages and clarification questions', self.text)
        self.assertIn('use the most recent natural-language user messages', self.text)
        self.assertIn('do not switch to English because this skill is written in English', self.text)


if __name__ == '__main__':
    unittest.main()
