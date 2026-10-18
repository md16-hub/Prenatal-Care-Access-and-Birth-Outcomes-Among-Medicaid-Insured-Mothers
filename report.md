# Prenatal Care Access and Birth Outcomes Among Medicaid Mothers

## Question
Do Medicaid mothers get less early prenatal care, and does that go with lighter, earlier births? Does it depend on where they live?

## Data
CDC WONDER Natality, 2024: 3,586,634 births, 1,439,510 of them paid by Medicaid. The file is grouped by county, payer and the month prenatal care began. That gives 626 units: 578 counties with 100,000+ people and 48 state pools of smaller counties (CDC lumps these together as "Unidentified Counties").

The file has no preterm or low-birth-weight rates, so I used what it does have:

| I wanted | I used |
|---|---|
| Preterm birth | average gestational age and its spread (SD) |
| Low birth weight | average birth weight (g) |
| Care adequacy | no prenatal care, or no care in the first trimester |
| Local access to care | county share of births with no first-trimester care |
| Community context | county share of births paid by Medicaid |

Poverty, hospital closures and provider shortages are not in the file, so I did not test them.

## Finding 1: Medicaid mothers miss early care, and no care at all is the biggest risk signal
- 33.9% of Medicaid births had no first-trimester care. For private insurance it was 14.7%. Self-pay was 44.5%.
- Births with no prenatal care are about 230 g lighter and 0.74 weeks shorter than births with care (model below).
- Medicaid births with no care average 2,961 g and 37.22 weeks. With care in months 1-3 they average 3,198 g and 38.17 weeks.
- The spread in gestational age is much wider with no care: 3.48 weeks versus 2.13. That points to more very early births. These births are 3.2% of Medicaid births.

![Dashboard 1](dashboards/care_access_gap.png)

## Finding 2: Late care does not explain the whole Medicaid gap
- In the same county, Medicaid births are 89 g and 0.15 weeks below private-insurance births. This holds in 97% of counties.
- Comparing only births where care started in months 1-3, the gap is still about 84 g.

![Dashboard 2](dashboards/medicaid_vs_private_gap.png)

## Finding 3: Where a Medicaid mother lives matters
- Average Medicaid birth weight runs from 3,044 g in Mississippi to 3,312 g in Alaska (states with 3,000+ Medicaid births). That is a 268 g spread for the same payer.
- Lowest: Mississippi, DC (3,070 g), Louisiana (3,082 g), Georgia (3,112 g), Alabama (3,113 g). Highest: Alaska, Washington (3,286 g), Oregon (3,279 g).
- Counties with the weakest early-care rates (46% with no first-trimester care) average 3,162 g for Medicaid births. Counties with the best (21%) average 3,221 g.
- Most of that county pattern is differences between states. Comparing counties inside the same state, the effect drops from 19 g to 7 g per standard deviation and is no longer significant (p = 0.08).

![Dashboard 3](dashboards/geography.png)

## Other things the data shows
- **Community context.** Medicaid births in the most Medicaid-heavy counties average 3,165 g, versus 3,208 g in the least Medicaid-heavy. That is 43 g apart for the same payer. It holds inside states (14 g lighter per standard deviation of county Medicaid share, p < 0.001). The file cannot say why.
- **Risks stack.** The 66 counties in the top quartile for both Medicaid share and missing early care (14.5% of births) average 3,192 g and 38.14 weeks. Counties in neither group average 3,265 g and 38.37 weeks.
- **Hot spots.** Among larger counties with 2,000+ Medicaid births and weak early-care rates, the lightest Medicaid births are in Orleans Parish LA (3,019 g), Fulton County GA (3,033 g), St. Louis County MO (3,039 g), East Baton Rouge Parish LA (3,050 g) and Shelby County TN (3,056 g).
- **Rural is not worse in absolute terms.** Small-county pools have slightly heavier babies overall (3,256 g vs 3,238 g), and Medicaid births there average about the same as in larger counties (3,186 g vs 3,181 g). But the Medicaid-vs-private gap is wider in small counties, about 112 g versus 87 g.
- **Self-pay is unclear.** Self-pay births have the best averages of any payer group even though they have the highest no-care rate. Nothing in the file explains it.

## Model
Cell-level regression on 10,191 county x payer x care-timing cells (Medicaid vs private only, known timing), weighted by births, standard errors clustered by county. Coefficients are grams and weeks, not odds ratios. Code is in `multivariate_model.py`.

| Predictor | Birth weight (g) | Gestational age (weeks) |
|---|---|---|
| Medicaid (vs private) | -87 | -0.19 |
| No prenatal care (vs care started) | -230 | -0.74 |
| Small-county pool (private births) | +28 | -0.11 |
| Medicaid x small-county pool | -24 | 0.00 (not significant) |

Adding state effects barely changes this (Medicaid -86 g, no care -216 g). Medicaid and no care each carry their own penalty. A small county is not a penalty by itself, but it adds about 19 to 24 g to the Medicaid gap.

## Limits
- **Averages, not rates.** A gap in average weight does not tell you the share of babies under 2,500 g or under 37 weeks.
- **Association, not cause.** The gaps are small (tens of grams, tenths of a week). The data is county-level, so it does not describe individual mothers.
- **One year.** No trends.
- **Care timing depends partly on the outcome.** A pregnancy that ends early has had less time for care to start, and late starters show longer gestation (39.1 weeks for month 9) for the same reason.
- **Suppressed cells.** Cells under 10 births are hidden, so no-care share is missing for 106 counties.
- **Small-county pools mix very different places**, so they are only a rough stand-in for rural.
- **Not testable here:** a preterm yes/no regression, a rural-urban map, or anything adjusted for poverty. The file has no individual records, no rural-urban code and no poverty measure.

## What this points to
These are readings of the numbers above, not tested interventions.
- Getting Medicaid mothers into care in the first trimester, and reaching the 3% who get none, targets the clearest risk.
- State and county differences are large, so priorities should differ by place. The hot-spot counties are where to look first.
- The community effect survives comparing within states, so conditions beyond appointment timing probably matter. That needs data from outside this file.
