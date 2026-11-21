# Game spec (for research briefs) — derived from the QuantCo "Claim to Fame" slides

N teams play repeated rounds (~13 min apart, ~22 h, so on the order of 100 rounds). Each round is one insurance
"case": description.txt (damage report), policy.txt (coverage/exclusions), invoices.pdf (line items with
quantity + unit but NO prices), optional images. Teams have ~60 s per round, so the pricing must be automated.

Per invoice line i a team submits TWO numbers (gross line total = qty x unit price, VAT incl.):
  a_i = charge price (what it bills EVERY other team as "handyman")
  b_i = acceptance limit (the most it will pay when ANY other team bills it, as "insurer")
Unsubmitted line => a=0,b=0. Missed round => b=0 (rejects everything) .

Hidden fair value t_i per line (set by claims experts; t=0 if excluded by policy / unrelated to the damage).
A charge is "fair" if a<=t, "inflated/fraud" if a>t.

Every ordered pair (handyman H -> insurer I) settles per line (money flows team to team, zero-sum):
  accepted (a<=b_I), fair (a<=t):      I pays H a                     (right call)
  accepted (a<=b_I), inflated (a>t):   I pays H min(a,c)  (cap c)     (wrong call; H pockets it)
  rejected (a>b_I),  fair (a<=t):      I pays H 1.5*a  (50% penalty)  (wrong call)
  rejected (a>b_I),  inflated (a>t):   nothing flows                  (fraud caught)
A team's score = total received as handyman - total paid as insurer, summed over all other teams, lines, rounds.
Winner = most money overall (+ <=1 page write-up + presentation). No cross-team collaboration, no attacking the platform.
Observation: a_i and b_i enter a team's payoff additively (a only affects what you RECEIVE, b only what you PAY),
so each is its own decision problem given beliefs about the other teams' b and a distributions.
Derived (to be checked): rejecting a charge is right iff P(fraud) > 1/3 (accept cost a vs reject cost 1.5*a*P(fair)).
Unknowns still pending: the case files/starter kit, EVALUATION_CRITERIA, whether per-round results/per-line ground truth
t or other teams' a,b are revealed after a round, the cap c, how many teams.
