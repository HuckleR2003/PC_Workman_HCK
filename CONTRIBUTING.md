# Contributing to PC Workman

Thank you for wanting to help. Bug reports, ideas and pull requests are all welcome.

## Reporting a bug or an idea

- Open an issue: https://github.com/HuckleR2003/PC_Workman_HCK/issues
- Say what you did, what you expected and what happened, your Windows version and the PC Workman version
  (Settings, Build info).
- `data/logs/startup.log` and `data/logs/errors.log` next to the exe help a lot. Check them for anything
  personal before you attach them.
- Security problems: do not open a public issue, see [SECURITY.md](SECURITY.md).

## Pull requests

- Keep one change per pull request, with a test when the change has logic in it (`py -m unittest discover -s tests`).
- Code, comments and commit messages in English. The interface is Polish and English: every visible text
  goes through the translation helpers.
- Nothing that kills, suspends or changes system processes, services or settings without the user's
  explicit consent and an undo.

## Licence of contributions (contributor agreement)

PC Workman is licensed under the GNU General Public License v3.0 only (see [LICENSE](LICENSE)).
The project also needs to be able to offer a separate commercial licence, so that it can pay for itself.

By opening a pull request you agree that:

1. your contribution is your own work, or you have the right to submit it;
2. it is licensed to everyone under GPL-3.0-only, like the rest of the code;
3. you also grant Marcin Firmuga (HCK_Labs) a permanent, worldwide, royalty-free right to use, change and
   relicense your contribution, including under a commercial licence, as part of PC Workman and its
   related products.

You keep the copyright of your contribution and can use it anywhere else as you like.
If you do not agree with point 3, say so in the pull request before it is merged.
