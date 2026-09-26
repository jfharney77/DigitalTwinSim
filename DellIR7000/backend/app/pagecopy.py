"""The thermal bring-up page's own prose — pure data, leveled like the rest.

The page intro, the hint under the diagram, and the notes under the heat
balance and playback panels used to be hard-coded in the frontend, so they
read in one register whatever level the reader had chosen. They ride on the
``GET /api/thermal`` response instead and resolve in ``main.py`` like every
other block. Every claim here is one ``tests/test_engine.py`` makes.
"""

from __future__ import annotations

from .leveling import L
from .models import PageCopy

PAGE_COPY = PageCopy(
    intro=L(
        novice=(
            "Nothing on this page boots up. It shows a rack of computers cooled "
            "by liquid being made ready, the way you would bring a small water "
            "system into service. First the pipes are filled and the air is let "
            "out. Then the pumps start, every pipe is checked for leaks and for "
            "its share of liquid, and the cooling door on the back is switched "
            "on. Only after all that are the computers allowed to turn on and "
            "make heat. From then on one rule holds: all the heat that comes in "
            "goes out, exactly. Press Run and watch the numbers add up."
        ),
        plain=(
            "Nothing here boots; the story is heat. A rack this size, about a "
            "quarter of a million watts, is a small pumping plant, and it is "
            "brought into service like one: fill the pipes and get the air out, "
            "start the pumps, check every branch (the pipe run to one bay) for "
            "leaks and for flow, and switch on the rear door, a water coil and "
            "fans that catch the warm air. Only then do the computers power on. "
            "From that moment heat in equals heat out on every step, exactly. "
            "Play the trace and watch the books balance."
        ),
        standard=(
            "Nothing in this twin boots; the plot is physics. A quarter-megawatt "
            "rack is a small hydraulic plant, and it is commissioned like one: "
            "fill the loop and pull the air out, start the pumps, leak-check "
            "and verify flow through every branch, bring the rear-door heat "
            "exchanger online, and only then let the IT load arrive. From that "
            "moment one law runs the show: heat in equals heat out, on every "
            "step, exactly. Play the trace and watch the books balance."
        ),
        technical=(
            "A commissioning trace, not a boot: fill and degas, pumps, "
            "per-branch leak and flow verification, rear-door coil online, then "
            "IT load. Once load exists, cold-plate heat plus door heat equals IT "
            "load on every step, exactly."
        ),
        expert=(
            "Commissioning trace: fill, pump, verify, door, load. Cold plate + "
            "door == IT load, every step, zero tolerance."
        ),
    ),
    hint=L(
        novice=(
            "The bright blocks are the parts working at this step. Watch the "
            "pipes get filled, pumped and checked before there is any heat at "
            "all. Once the computers turn on, look at the Heat balance panel: "
            "the two heat-out numbers always add up to the heat-in number. "
            "Click a block to see what it is; every block is described under "
            "Inside the loop."
        ),
        standard=(
            "Highlighted blocks are the parts doing work at this step. Watch "
            "the loop prove itself before any heat exists (fill, pump, verify), "
            "and watch the heat-balance panel once load arrives: cold plates "
            "plus rear door always equals the IT load. Click a block to pin "
            "what it is; every block is described under Inside the loop."
        ),
        expert=(
            "Lit blocks are active this step. Click a block to pin it; all are "
            "described under Inside the loop."
        ),
    ),
    balance_note=L(
        novice=(
            "Heat cannot vanish. The heat taken by the cooling plates plus the "
            "heat caught by the rear door always adds up to the load exactly, "
            "and the twin checks this on every step. Both end up in the same "
            "liquid, so the flow follows the whole load, and the liquid comes "
            "back about 10 degrees warmer than it left, which is what the loop "
            "temperature rise on this panel counts. The numbers are "
            "illustrative: they show the shape of a real rack, not measurements "
            "of one."
        ),
        standard=(
            "Energy is conserved: cold-plate heat plus rear-door heat equals "
            "the IT load exactly, on every step. Both paths reject into the one "
            "rack loop, so coolant flow follows the whole load, and the loop "
            "temperature rise shown is that load divided by flow times the "
            "coolant's heat capacity — PG25, a 25% propylene-glycol and water "
            "mix, carries about 66 W per L/min for each kelvin of rise, and a "
            "rise of 1 K is a rise of 1 °C. "
            "Values are illustrative, meant to show shape and order of "
            "magnitude."
        ),
        expert=(
            "Cold plate + door == IT load, exact, every step. Both reject into "
            "the rack loop; rise = Q / (flow x ~66 W per L/min per K, PG25). "
            "Values illustrative."
        ),
    ),
    playback_note=L(
        novice=(
            "The steps are always the same and in the same order; Run simply "
            "plays them. Step moves one at a time. The slowest real-world "
            "stage, checking every pipe for leaks and flow, stays on screen "
            "longer."
        ),
        standard=(
            "The commissioning sequence is fixed; Run only plays it back. Step "
            "walks one event at a time, and the long real-world stage "
            "(per-branch leak and flow verification) dwells on screen longer."
        ),
        expert="Fixed sequence. Run plays, Step advances one; verification dwells.",
    ),
)
