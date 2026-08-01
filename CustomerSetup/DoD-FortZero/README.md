# US Department of Defense — Project Fort Zero validation

Open `setup.html` in a browser for the drawing.

The publicly reported facts: in April 2025, Dell's Project Fort Zero completed the US
Department of Defense's assessment under the DoD Zero Trust Reference Architecture (ZTRA)
and achieved **Target Level** validation as a sovereign, on-premises private cloud —
tested by withstanding sophisticated attack. The program was announced in 2023 with an
ecosystem of 30+ partners.

This is the collection's odd one out: the assessed "setup" is a decision architecture, not
a rack row, so the drawing is the DoD's seven co-equal pillars around one policy engine,
with the assessment team drawn already inside — and deliberately no perimeter anywhere.
The `DellFortZero/` twin enforces that absence with a test
(`test_nothing_is_drawn_as_a_perimeter`), and this page honors it.

Twins referenced by the drawing (frontend ports — start each with its `scripts/start_all.sh`):

| Block | Twin | Port |
|---|---|---|
| Pillars, policy engine, contained breach | `DellFortZero/` | 5195 |
| Hardware root of trust (inferred) | `DellIDRAC/` | 5177 |
| Private-cloud substrate (representative) | `DellPrivateCloud/` | 5198 |
| The servers (representative) | `DellPowerEdgeR760/` | 5174 |

Sources:
- https://www.dell.com/en-us/dt/corporate/newsroom/announcements/detailpage.press-releases~usa~2025~04~dell-technologies-achieves-us-department-of-defense-validation-for-zero-trust-solution.htm
- https://investors.delltechnologies.com/news-releases/news-release-details/dell-technologies-project-fort-zero-transform-security
- https://www.executivebiz.com/articles/dell-zero-trust-cybersecurity-platform
