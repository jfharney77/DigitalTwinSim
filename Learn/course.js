// The course as data. Everything after the assignment below is plain JSON,
// so Learn/tests/test_links.py can json.loads it and pin every link, cite and
// quoted number against the code. Edit it by hand; keep it valid JSON.
window.COURSE = {
 "version": 1,
 "title": "Learn the twins",
 "modules": [
  {
   "id": "M1",
   "title": "The roofline",
   "core": true,
   "idea": {
    "standard": "Whether a kernel — one program run on the GPU, this matmul — is limited by compute or by memory is a comparison: the kernel's multiply-adds per byte against one number of the chip, its ridge point. It is not a property of either alone.",
    "novice": "A chip can be held up by waiting for data (memory-bound) or by doing arithmetic (compute-bound). Which one wins depends on how much arithmetic the job gets for each byte fetched, measured against a break-even number that belongs to the chip."
   },
   "prereqs": [],
   "background": {
    "standard": "A matrix multiply is N³ multiply-adds, and data has to be loaded before anything can use it. Kernel above means a program run on the GPU, not an operating-system kernel. The simulator writes each multiply-add as a MAC (multiply-accumulate), so intensity appears on screen as MAC/byte.",
    "novice": "Multiplying two grids of numbers (matrices) is a lot of small multiply-then-add sums: for N-by-N grids, N × N × N of them. The numbers must be fetched from memory before the chip can use them. The screen shortens multiply-add to MAC (multiply-accumulate), so a line reading MAC/byte is sums per byte."
   },
   "objectives": [
    {
     "standard": "Define arithmetic intensity (multiply-adds per byte moved) and the ridge point (the die's multiply-adds per cycle divided by the bytes it can load per cycle).",
     "novice": "Say what arithmetic intensity is (how many multiply-add sums the job does for each byte it fetches) and what the ridge point is (the chip's break-even value of that number)."
    },
    {
     "standard": "Predict the memory-bound or compute-bound regime from those two numbers.",
     "novice": "Tell from those two numbers whether the chip is waiting for data (memory-bound) or busy with arithmetic (compute-bound)."
    },
    {
     "standard": "Explain why changing the playback speed never changes a number on the screen.",
     "novice": "Explain why making the animation faster or slower never changes any number on the screen."
    }
   ],
   "entries": [
    {
     "twin": "GPU",
     "port": 5173,
     "pageTitle": "GPU Matmul Visualizer",
     "name": "GPU die simulator",
     "links": [
      {
       "kind": "root",
       "label": "Open the simulator",
       "how": {
        "standard": "Leave everything as it opens: Generic-128, Matrix multiply, N 4, tile size 2, fp32. In the Roofline box read regime, intensity, ridge point and bytes moved. Change Precision (dtype) from fp32 to int8 and read them again. Put it back to fp32, drag the tile size to 1 and read intensity and bytes moved. Then switch the die profile to RTX-4060-Laptop and repeat the int8 change. Back on Generic-128 at fp32, read the load cycles and compute cycles lines in the same box, and watch them as you set Precision to fp16. The info dot beside the Run controls says what the Speed slider does.",
        "novice": "Leave everything as it opens (Generic-128, Matrix multiply, N 4, tile size 2, fp32). Find the box called Roofline and read four lines: regime, intensity, ridge point and bytes moved. The ridge point is the chip's break-even: when intensity is below it the chip waits on memory, and when intensity reaches it the chip is busy with arithmetic. Now change Precision (dtype) from fp32 to int8 and read the four lines again. Put it back to fp32, drag the tile size to 1 (a tile is the small block of the grid loaded at a time) and watch intensity and bytes moved. The box holds more lines than those four; two of them are load cycles and compute cycles, the turns the chip spends fetching and the turns it spends adding. Read that pair at fp32, then set Precision to fp16 and read it again. Ignore the rest for now — each line has its own small i if you want it. Last, open the small i beside the Run controls and read what Speed does."
       }
      },
      {
       "kind": "lesson",
       "hash": "#live/tour",
       "lesson": "the-roof",
       "label": "The CUDA lesson tour",
       "how": {
        "standard": "Press Next until the lesson called Find the roof (a recording, replayed). Its caption divides the copy's footprint — 0.537 GB, fixed by the lesson's source code, not a read-out — by the one figure the counters do show, Kernel time 2.20 ms, and gets about 244 GB/s against the laptop GPU's rated 256 GB/s. A separate line in the simulator's Roofline box, last bandwidth measurement, carries whatever a live run last posted to this backend, so it need not match the recording. The lessons before it are about thread blocks and placement; this module does not need them.",
        "novice": "Press Next until the lesson called Find the roof, and read its caption (it is a recording, played back). A program that only copies data measures how fast the memory can go: the caption divides the amount copied, 0.537 gigabytes, by the time on screen, 2.20 milliseconds, and gets about 244 gigabytes a second. The amount copied is not on the screen — it is set by the program's own code, and the caption tells you so. The laptop GPU's memory is rated 256 gigabytes a second, so the copy came close to the limit. That limit is the memory half of the ridge point. You can skip the lessons before it; they are about a different topic."
       }
      }
     ]
    }
   ],
   "predict": {
    "q": {
     "standard": "On the Generic-128 die with N 4, tile size 2 and fp32, the simulator reads intensity 0.25 against a ridge point of 0.50, so the kernel is memory-bound. Keep the matmul and the tile size the same and change only the data type, from fp32 to int8. Does the kernel stay memory-bound?",
     "novice": "The simulator opens on a job where the chip gets 0.25 sums for each byte it fetches. This chip's break-even (its ridge point) is 0.50, so it is waiting on memory (memory-bound). Same job, same settings. You only shrink each number from 4 bytes to 1 byte. Is the chip still waiting on memory?"
    },
    "options": [
     "Yes, it stays memory-bound",
     "No, it becomes compute-bound",
     "It becomes compute-bound only if N also grows"
    ],
    "answer": 1,
    "reveal": {
     "standard": "No. A quarter of the bytes carry the same multiply-adds, so intensity goes from 0.25 to 1.00 and clears the ridge at 0.50. The answer belongs to the pair, not to the kernel: on the RTX-4060-Laptop profile the ridge point is 2.00, the same change again reaches 1.00, and the kernel stays memory-bound. One caution before you carry this to real silicon: here the ridge is held still while intensity moves, because the die's multiply-adds per cycle do not depend on the data type. On a part with tensor cores they do. Set Execution to tensor on RTX-4060-Laptop and the ridge moves with the format: fp16 gives a ridge of 8.00 against intensity 0.50, and int8 a ridge of 16.00 against intensity 1.00 — each drop in precision leaves the kernel further below the ridge, not above it. (In tensor mode fp32 is greyed out; that die has no fp32 tensor path.) The twin's Execution and Precision info dots say why: low precision buys arithmetic throughput faster than it saves bytes, which usually makes a kernel more memory-bound, not less.",
     "novice": "No. Each number is a quarter of the size, so the same sums need a quarter of the bytes. Sums per byte go from 0.25 to 1.00, which is past this chip's break-even of 0.50, so the chip stops waiting on memory and is busy with arithmetic (compute-bound). On a chip with a higher break-even the same change would not be enough: the laptop GPU in the list has a ridge point of 2.00 and stays memory-bound. One caution: this works because the break-even stays put while sums per byte move. On real chips with special arithmetic units (tensor cores) the break-even moves too, and usually further. Switch Execution to tensor on the laptop GPU and watch the break-even climb as the numbers get smaller: 8.00 at fp16, 16.00 at int8, while sums per byte only reach 0.50 and 1.00. Smaller numbers bought more arithmetic than they saved fetching, so the chip waits on memory even harder."
    },
    "cite": [
     "GPU/backend/tests/test_bandwidth.py::test_regime_flips_with_dtype",
     "GPU/backend/tests/test_profiles.py::test_ridge_point_right_of_generic"
    ]
   },
   "checks": [
    {
     "q": {
      "standard": "Shrinking the tile moves arithmetic intensity which way, and why?",
      "novice": "You dragged the tile size from 2 to 1. Which way did intensity go, and what happened to bytes moved?"
     },
     "a": {
      "standard": "Down: 0.25 at tile size 2, 0.13 at tile size 1, with bytes moved going from 256 to 512. A smaller tile reuses each loaded value fewer times, so more bytes move for the same multiply-adds. Each trip is lighter; there are more of them.",
      "novice": "Down, from 0.25 to 0.13, and bytes moved doubled from 256 to 512. With a smaller tile each fetched number is used fewer times before it is fetched again, so the same sums cost more fetching. Each trip to memory is lighter, but there are many more trips."
     },
     "cite": [
      "GPU/backend/tests/test_bandwidth.py::test_smaller_tiles_lower_intensity_toward_memory_bound"
     ]
    },
    {
     "q": {
      "standard": "In a memory-bound run, which total is larger: load cycles or compute cycles? What does the twin call a tie?",
      "novice": "When the chip is waiting on memory (memory-bound), which does it spend more turns on: loading data or computing? The screen calls those turns load cycles and compute cycles. What does the simulator say when the two are equal?"
     },
     "a": {
      "standard": "Load cycles. Intensity below the ridge point is the same statement as load cycles exceeding compute cycles. At the ridge they are equal (fp16 at tile size 2 gives 16 and 16, intensity 0.50), and the twin calls that compute-bound.",
      "novice": "Loading — load cycles 32 against compute cycles 16 as it opens. Being below the break-even and spending more turns loading than computing are the same fact said two ways. When the two lines are exactly equal (set Precision to fp16: 16 and 16, intensity 0.50) the simulator calls it compute-bound."
     },
     "cite": [
      "GPU/backend/tests/test_bandwidth.py::test_regime_consistent_with_cycle_totals"
     ]
    },
    {
     "q": {
      "standard": "Where does the timer that animates the die live, and why there?",
      "novice": "You change Speed and the animation runs faster. Which numbers on the screen change, and why?"
     },
     "a": {
      "standard": "In the browser, in GPU/frontend/src/App.tsx. The engine returns a finished list of states and holds no timers, so the same inputs always give the same trace: it can be replayed, stepped and tested, and speed is a viewing choice. The component suite enforces it by parsing the engine's imports; nothing but pure modules is allowed in.",
      "novice": "None of them. The simulator's back end works out every frame in advance and hands over the finished list; the web page just flips through it at the speed you chose. Because the list is worked out once, it can be replayed and checked, and Speed is only a choice about how you watch it."
     },
     "cite": [
      "GPU/backend/tests/test_power.py::test_engine_stays_pure_with_power"
     ]
    }
   ],
   "pins": [],
   "bridge": {
    "text": {
     "standard": "A GPU is a chip. Before it computes anything, the box around it has to power on, and in a server that box has its own small computer that never sleeps. The next module turns on an R760.",
     "novice": "A GPU is one chip inside a bigger machine. Next, watch that machine switch on, starting with the small helper computer that is awake even when the server looks off."
    },
    "next": "M2"
   }
  },
  {
   "id": "M2",
   "title": "A server wakes up",
   "core": true,
   "idea": {
    "standard": "A plugged-in server is never really off, and one stage of switching it on dwarfs the rest.",
    "novice": "As soon as a server is plugged in, a small management computer inside it is already running. And when the server is switched on, one stage takes far longer than the others; it is not the one most people guess."
   },
   "prereqs": [],
   "background": {
    "standard": "A server has CPUs, memory modules (DIMMs), drives and fans.",
    "novice": "A server is a computer built for a rack. It has processors (CPUs), memory modules, drives and fans."
   },
   "objectives": [
    {
     "standard": "Put the power-on phases in the order the twin labels them, word for word: off — AC only, standby power, iDRAC booting, host power-on, POST, boot device, operating system.",
     "novice": "Put the stages in order, using the words on the model's own screen: off — AC only, standby power, iDRAC booting (the helper computer), host power-on (the main computer), start-up checks (POST), boot device, operating system."
    },
    {
     "standard": "Explain why the baseboard management controller (BMC; Dell's is called iDRAC) boots before the host, meaning the server's main processors and everything they run.",
     "novice": "Explain why the small helper computer starts before the main computer does. Its general name is a baseboard management controller, BMC for short; Dell's is called iDRAC."
    },
    {
     "standard": "Name the longest stage, say why it cannot be hardcoded, and say when it has to run again.",
     "novice": "Name the slowest stage, say why it cannot be worked out once at the factory, and say when it has to be done again."
    }
   ],
   "entries": [
    {
     "twin": "DellPowerEdgeR760",
     "port": 5174,
     "trace": "poweron",
     "name": "PowerEdge R760 power-on",
     "pageTitle": "PowerEdge R760 Inside",
     "links": [
      {
       "kind": "tour",
       "id": "memory-training",
       "label": "Guided tour, at DDR5 memory training",
       "lockedLabel": "Guided tour, at the long pause",
       "how": {
        "standard": "The link opens the tour part-way through. Press Previous to reach the first beat if the chassis is new to you.",
        "novice": "New to this? The link opens the tour in the middle. Press Previous until the first beat and watch the tour through before you open the trace below."
       }
      },
      {
       "kind": "step",
       "value": 8,
       "expectPhase": "post",
       "label": "Power-on trace, paused on memory training",
       "lockedLabel": "Power-on trace, paused on the longest stage",
       "how": {
        "standard": "The link counts steps from zero, so it lands on what the twin's Telemetry panel calls step 9 / 15. The twin numbers steps from one, and so do the answers below.",
        "novice": "The model counts its steps from one, and the answers below use the numbers you see on its screen."
       }
      }
     ]
    },
    {
     "twin": "DellIDRAC",
     "port": 5177,
     "trace": "bringup",
     "name": "iDRAC9 bring-up",
     "pageTitle": "iDRAC9 Inside",
     "links": [
      {
       "kind": "tour",
       "id": "always-on",
       "label": "Guided tour, at the always-on beat"
      },
      {
       "kind": "step",
       "value": 8,
       "expectPhase": "services",
       "label": "Bring-up trace, paused on Lifecycle Controller init",
       "lockedLabel": "Bring-up trace, paused on its longest stage"
      }
     ],
     "note": {
      "standard": "The two twins were drawn separately and their illustrative numbers are not reconciled. Watts: the R760 reads 15 W on the step it labels standby power and 20 to 22 W across the two it labels iDRAC booting — whole-chassis figures, host off throughout — while the iDRAC trace reads 4 to 8 W for the management controller's own domain. Clocks: both start when AC is applied, and they still disagree. The R760 has iDRAC taking a hardware inventory at t+45 s, but they are not describing the same work — that inventory is the sideband walk over I2C and PMBus, while the iDRAC twin's t+55 s step is the Lifecycle Controller reconciling its stored repository against it. Nothing the R760 shows waits on that: its host power-on is at t+60 s, after both.",
      "novice": "This second model zooms in on the helper computer alone. The two models were built separately, so their numbers do not line up. Power: the first reads 15 watts on the step it calls standby power and 20 to 22 watts while the helper computer boots, and those are figures for the whole server; this one reads 4 to 8 watts for the helper computer by itself. Time: both clocks start when the cords go in, but the two models count different work, so do not try to match one step against the other. All of the figures are illustrative."
     }
    }
   ],
   "predict": {
    "q": {
     "standard": "Which stage of the R760 power-on takes longest: the iDRAC boot, DDR5 memory training, or the operating system load?",
     "novice": "Switching on a server has several stages. Which one takes the longest: the helper computer (iDRAC) starting, the memory (DDR5) learning its timing, or the operating system loading?"
    },
    "options": [
     {
      "standard": "The iDRAC boot",
      "novice": "The helper computer (iDRAC) starting"
     },
     {
      "standard": "DDR5 memory training",
      "novice": "The memory (DDR5) learning its timing, called memory training"
     },
     {
      "standard": "The operating system load",
      "novice": "The operating system loading"
     }
    ],
    "answer": 1,
    "reveal": {
     "standard": "DDR5 memory training, inside POST: step 9 of 15 on the twin's screen. Its text says it is the longest stage, the elapsed clock jumps from t+70 s to t+180 s across it, and Run dwells there. The dwell is the trace's cycle cost — a relative weight, not seconds: 6 here, the unique maximum. It is ranked to follow the printed durations rather than scaled to them, so the long stages hold the screen and the short ones flick past, but 110 s does not dwell thirteen times as long as 8 s. What training finds is the per-lane electrical set — signal timing and voltage on each wire — whose margins are specific to this board and these parts and too fine to hardcode. The results are cached, so later boots are much faster, and training runs in full again when the cache no longer applies, such as after a memory change.",
     "novice": "The memory learning its timing (step 9 of 15 on the model's screen). On each wire between the processor and every memory module, the signal timing and voltage have to be tuned for this particular board before the computer can trust what it reads, and that takes longer than anything else: the model's clock jumps from 70 seconds to 180 seconds on that one step, and Run lingers there. The results are saved, so later starts are much quicker."
    },
    "cite": [
     "DellPowerEdgeR760/backend/tests/test_engine.py::test_memory_training_is_the_longest_stage"
    ]
   },
   "checks": [
    {
     "q": {
      "standard": "Does iDRAC come up before or after someone presses the power button?",
      "novice": "Does the helper computer (iDRAC) start before or after someone presses the power button?"
     },
     "a": {
      "standard": "Before. On the twin's screen the phase labelled iDRAC booting is steps 3 and 4 of 15, and host power-on begins at step 5. The second iDRAC step takes a hardware inventory while the host is still off.",
      "novice": "Before. On the model's screen, steps 3 and 4 of 15 are labelled iDRAC booting, and main power does not come on until step 5. In step 4 the helper computer is already listing the server's parts while the server itself is still off."
     },
     "cite": [
      "DellPowerEdgeR760/backend/tests/test_engine.py::test_trace_invariants"
     ]
    },
    {
     "q": {
      "standard": "In the iDRAC twin, what is the most the counter labelled BMC domain draw ever reads?",
      "novice": "In the iDRAC model, find the counter labelled BMC domain draw (BMC is the general name for a helper computer like iDRAC). What is the most it ever reads?"
     },
     "a": {
      "standard": "8 W. The host never powers on during iDRAC's own bring-up, so nothing larger ever draws; the twin's test would fail the trace above 20 W. This is the controller's own domain, not the 15 to 22 W the R760 twin shows for the whole chassis with its host off.",
      "novice": "8 watts, about a night-light. The big server is never switched on in this model, so nothing bigger ever draws power. The 15 to 22 watts you saw in the first model was for the whole server with its main power off, not the helper computer alone."
     },
     "cite": [
      "DellIDRAC/backend/tests/test_engine.py::test_host_never_powers_on"
     ]
    },
    {
     "q": {
      "standard": "Which iDRAC stage is the longest, and how can you tell from the screen?",
      "novice": "Which stage of the helper computer's start-up is the longest, and how can you tell from the screen?"
     },
     "a": {
      "standard": "Lifecycle Controller initialization, step 9 of 14 on screen. Run lingers on it and the elapsed clock jumps 25 s across it, from t+30 s to t+55 s, more than on any other step. In the trace that dwell is a cycle cost of 6, the unique maximum.",
      "novice": "Lifecycle Controller initialization, step 9 of 14 on the screen. Run lingers on it, and the clock jumps 25 seconds on that one step, from 30 to 55 seconds, more than on any other."
     },
     "cite": [
      "DellIDRAC/backend/tests/test_engine.py::test_lifecycle_controller_is_the_longest_stage"
     ]
    },
    {
     "q": {
      "standard": "Why can the R760's longest stage not be hardcoded, and why is a second boot faster?",
      "novice": "Why can the memory's timing not be set once at the factory, and why is the second start-up quicker?"
     },
     "a": {
      "standard": "The signal margins at DDR5 speeds are specific to this board and these parts, too fine to hardcode, so the processors have to find them by training. The results are cached, so later boots skip most of the work until the cache no longer applies.",
      "novice": "At these speeds the right timing depends on this exact board and these exact memory modules, so the server has to find it by trying. It saves what it learned, so the next start-up is much quicker."
     },
     "cite": [
      "DellPowerEdgeR760/backend/tests/test_engine.py::test_memory_training_is_the_longest_stage"
     ]
    }
   ],
   "pins": [
    {
     "twin": "DellPowerEdgeR760",
     "step": 8,
     "field": "cycle_cost",
     "value": 6
    },
    {
     "twin": "DellPowerEdgeR760",
     "step": 3,
     "field": "phase",
     "value": "bmc"
    },
    {
     "twin": "DellPowerEdgeR760",
     "step": 4,
     "field": "phase",
     "value": "poweron"
    },
    {
     "twin": "DellIDRAC",
     "agg": "max",
     "field": "power_watts",
     "value": 8
    },
    {
     "twin": "DellIDRAC",
     "step": 8,
     "field": "cycle_cost",
     "value": 6
    }
   ],
   "bridge": {
    "text": {
     "standard": "The R760 reached its operating system idling with the fans at a quarter speed. Now leave it running and warm the room. The next module is the same machine in the physics simulator.",
     "novice": "The server is on and quiet. Next, keep it running and make the room hotter, and watch what the fans do about it."
    },
    "next": "M3"
   },
   "failures": [
    {
     "twin": "DellIDRAC",
     "port": 5177,
     "trace": "bringup",
     "name": "iDRAC9: a firmware update that rolls back",
     "scenario": "firmware-update-rollback",
     "at": {
      "kind": "step",
      "value": 7,
      "expectPhase": "bootcheck"
     },
     "label": "Firmware rollback trace, paused where the new image fails its boot check",
     "lockedLabel": "Firmware rollback trace, paused part-way through the update",
     "how": {
      "standard": "It opens on step 8 of 12, the boot check. Keep stepping: the message identifiers quoted below are on step 11, iDRAC returns on the old version, and step 12 is what the administrator is left with. Watch the bootable-images counter on the way — it reads 2 again on step 5, and that step's own text says why that count is wrong.",
      "novice": "It opens part-way through, on screen 8 of 12. Press Step to carry on to the end: screen 11 is the management computer coming back, and screen 12 is what is left for whoever has to fix it. Watch the count of good copies as you go — screen 5 explains why the count there cannot be trusted."
     },
     "q": {
      "standard": "An administrator pushes an iDRAC firmware update to a server running production workloads. iDRAC restarts to take it, and the new image fails its boot check. What happens to the workload on the host, and how many bootable iDRAC images are left at the end?",
      "novice": "Someone updates the small management computer inside a busy server. The update turns out to be bad and the management computer has to restart. Does the work the server is doing stop? And how many good copies of the management software are left afterwards?"
     },
     "options": [
      {
       "standard": "The host reboots with iDRAC; two images remain",
       "novice": "The server restarts along with the management computer; two good copies remain"
      },
      {
       "standard": "The host keeps running; one bootable image remains",
       "novice": "The server keeps working; one good copy remains"
      },
      {
       "standard": "The host keeps running; two images remain, as before",
       "novice": "The server keeps working; two good copies remain, as before"
      }
     ],
     "answer": 1,
     "a": {
      "standard": "The host stays powered on every step. Dell's guidance is that only the iDRAC reboots and the running operating system is not affected; people in the room may notice the fans ramp while it is away. What is lost is the management plane, for a bounded time: 120 s in the trace (illustrative); the twin's own test fails the trace if it exceeds 300 s. The update was signature-verified and written only to the inactive partition, so iDRAC comes back on partition A and version 7.10.30.00, and the Lifecycle log line on step 11 carries SUP0516, RAC0182, then SUP0520. Only 1 of 2 images is bootable until a good image is flashed again. Three things here are weaker than the rest: Dell documents the two images but the automatic switch between them is inferred; that message sequence is published for an iDRAC10 case on 17G servers, and is carried here because the identifiers are Dell's common ones, not because it was observed on an iDRAC9; and real failures do not always end this cleanly. The twin's own step text says the same.",
      "novice": "The server's work carries on the whole time. Only the management computer restarts, and for about two minutes in this model (an illustrative figure) nobody can reach it remotely. The fans may get loud while it is away. The bad update was only ever written to the spare copy, so the management computer starts again from the old, untouched copy and reports the old version. The cost is that it now has one good copy instead of two, until someone installs a good update. Two honesty notes: the exact log messages the model shows come from Dell's write-up of a newer model, and real failures are sometimes messier than this."
     },
     "cite": [
      "DellIDRAC/backend/tests/test_firmware_rollback.py::test_the_host_power_state_never_changes",
      "DellIDRAC/backend/tests/test_firmware_rollback.py::test_there_is_always_one_bootable_image",
      "DellIDRAC/backend/tests/test_firmware_rollback.py::test_management_outage_is_real_and_bounded"
     ],
     "pins": [
      {
       "step": 10,
       "field": "managementOutageSeconds",
       "value": 120
      },
      {
       "step": 11,
       "field": "bootableImages",
       "value": 1
      },
      {
       "step": 11,
       "field": "runningVersion",
       "value": "7.10.30.00"
      },
      {
       "step": 7,
       "field": "hostPowered",
       "value": true
      }
     ]
    }
   ]
  },
  {
   "id": "M3",
   "title": "Heat in one box",
   "core": true,
   "idea": {
    "standard": "Fans are part of the load they cool, and fan power goes as the cube of fan speed.",
    "novice": "Fans use electricity too, so cooling a server makes it draw more power. Spinning a fan a little faster costs a lot more energy."
   },
   "prereqs": [
    "M2"
   ],
   "background": {
    "standard": "Power drawn by a server ends up as heat in the room.",
    "novice": "All the electricity a server uses ends up as heat in the room."
   },
   "objectives": [
    {
     "standard": "State the power balance the simulator holds at every one-second step: the component watts sum to the DC total, and wall (AC) power is DC divided by the power supplies' efficiency.",
     "novice": "Add up what every part of the server uses, and say how that total compares with what the meter at the wall reads."
    },
    {
     "standard": "Explain the fan-power feedback loop.",
     "novice": "Explain why hotter air makes the server use more electricity even though its work has not changed."
    },
    {
     "standard": "Predict what losing a fan costs.",
     "novice": "Say what it costs when one fan breaks."
    }
   ],
   "entries": [
    {
     "twin": "DellPowerEdgeR760Thermal",
     "port": 5203,
     "pageTitle": "R760 Power &amp; Thermal Simulator",
     "name": "R760 power and thermal simulator",
     "links": [
      {
       "kind": "scenario",
       "id": "fan-feedback",
       "title": "The fan-power feedback loop",
       "label": "The fan-power feedback loop",
       "how": {
        "standard": "The run starts at ×1; pick a faster speed. The inlet steps from 22 to 40 °C at t+180 s. Watch the fan power (overhead) row and the CPU power row, not only the wall total, and let the run reach its end: the before-and-after table keeps the t+179 s baseline, including total DC power, and its change column is the settled answer. Then turn on Explain mode and read the notes under wall power and under ΔT front→back; two of the checks below are answered there.",
        "novice": "The run starts slowly; pick a faster speed. Three minutes in, the room goes from 22 to 40 degrees. Watch the row called fan power (overhead) and the row called CPU power, not only the big wall-power number, and let the run reach the end. The table under the text remembers what every reading was just before the room heated up, so you can compare. Then switch on Explain mode and read the notes under wall power and under ΔT front→back (how much hotter the air is at the back than at the front)."
       }
      },
      {
       "kind": "scenario",
       "id": "kill-a-fan",
       "title": "Kill a fan",
       "label": "Kill a fan",
       "how": {
        "standard": "One fan of six fails at t+180 s under HPC load. Read fan power (overhead) in the before-and-after table, and airflow in the instruments. Then run the two-fan case yourself: pick the Balanced build and the HPC workload at the default 22 °C inlet, run to about t+240 s so the boost is over and the fans have stopped hunting, take your baseline there, and click two fans in the chassis drawing to fail them. Reading before t+240 s mixes the end of the boost into the comparison. The twin also grades this one: open Labs in the header and pick \"Lose a fan, keep the clocks\".",
        "novice": "One of the six fans breaks three minutes in. Read the fan power row in the table, and the airflow reading in the instruments. Then try two broken fans yourself: choose the Balanced build and the HPC workload (a heavy computing job) with the room at 22 degrees, let the run reach about four minutes so the first-minute sprint is over and the fans have stopped hunting, write down the readings there, and then click two fans in the drawing to break them. Reading earlier than that mixes the end of the sprint into your comparison. The simulator can also mark this exercise for you: open Labs at the top of the page and pick \"Lose a fan, keep the clocks\"."
       }
      }
     ]
    }
   ],
   "predict": {
    "q": {
     "standard": "The workload never changes and the processors' own power does not move. Three minutes in, the inlet air rises from 22 to 40 °C. The wall meter reads about 715 W before the step. What does it read after?",
     "novice": "The server keeps doing exactly the same work, and the processors keep using the same electricity. Then the room goes from 22 to 40 degrees. The meter at the wall reads about 715 watts before that. What does it read after?"
    },
    "options": [
     "About 715 watts — the work has not changed",
     "About 765 watts",
     "About 915 watts"
    ],
    "answer": 1,
    "reveal": {
     "standard": "About 765 W — 767 W in this run, up roughly 50 W at constant work. The fans ramp from just over half speed to about 90% to hold the silicon at temperature, and fan watts are part of the DC sum at every one-second step, so fan power goes from about 16 W to about 65 W while CPU power does not move (illustrative). The cube law sets the size of the bill: near the top of the fan curve it costs this much, near the bottom almost nothing. Read the CPU row as the model's choice, not the hall's: here CPU power is a function of utilisation alone, while real silicon leaks more when it is hot, so a real box would rise a little more than the fan term alone.",
     "novice": "About 765 watts — 767 in this run, roughly 50 watts more for exactly the same work. The fans have to spin faster to keep the chips cool, and the fans' own electricity is part of the bill: they go from about 16 watts to about 65 watts while the processors stay where they were. Spinning a fan a little faster costs a lot more, which is why the extra 50 watts is nearly all fans. One thing to know: in this model the processors use the same watts hot as cold. Real chips leak a little more when hot, so a real server would rise slightly more than this one."
    },
    "cite": [
     "DellPowerEdgeR760Thermal/backend/tests/test_engine.py::test_guided_fan_feedback_raises_wall_power_at_constant_work",
     "DellPowerEdgeR760Thermal/backend/tests/test_engine.py::test_power_balance_every_tick"
    ]
   },
   "checks": [
    {
     "q": {
      "standard": "On the Balanced build under HPC load at 22 °C inlet, fail two of the six fans. Do the CPUs throttle?",
      "novice": "In the simulator pick the Balanced build and the HPC workload, then click two fans to break them. Do the processors have to slow down to stay cool?"
     },
     "a": {
      "standard": "No. The four survivors ramp from about 56% to about 84% and hold the CPUs at 85 °C at full clocks; fan power more than doubles, from about 16 W to about 35 W (both readings settled, so take the baseline after about t+240 s and the new figure a minute or two after the failure). The margin is the inlet: at 35 °C the four survivors pin at 100% and the CPUs run about 5 °C hotter, still under the 98 °C throttle line (illustrative).",
      "novice": "No. The four remaining fans spin faster (about 84% instead of 56%) and the processors carry on at full speed. The price is fan power, which more than doubles. In a hotter room the four fans would run flat out and the processors would get warmer."
     },
     "cite": [
      "DellPowerEdgeR760Thermal/backend/tests/test_engine.py::test_fan_failure_survivors_ramp"
     ]
    },
    {
     "q": {
      "standard": "Why do five fans at a higher speed use more power than six at a lower speed?",
      "novice": "Why do five fans working harder use more electricity than six fans taking it easy?"
     },
     "a": {
      "standard": "The heat load fixes the airflow the box needs, and airflow goes linearly with speed, so five fans must each run at 6/5 of the old speed. Fan power goes with the cube of speed: 5 × (6/5)³ is 8.64 against 6, or 1.44 times. The kill-a-fan run shows it: fan power (overhead) goes from about 16 W to about 23 W while airflow stays at about 71 CFM. The 1.44 is this model's arithmetic, not a machine's: it adds the survivors' airflow linearly, with no system curve and no leak back through the stopped rotor, so real N+1 cover costs more than this (the twin's footnote says so).",
      "novice": "Doubling a fan's speed moves twice the air but costs eight times the electricity. The server still needs the same amount of air, so five fans each have to spin faster than six did, and that extra speed is expensive. In the run, fan power goes from about 16 to about 23 watts while the airflow stays the same. Be careful carrying that size of cost to real hardware: this model simply adds up the air the running fans move, so the survivors make up the loss exactly, and a real machine recovers less."
     },
     "cite": [
      "DellPowerEdgeR760Thermal/backend/tests/test_engine.py::test_guided_kill_a_fan_costs_fan_watts"
     ]
    },
    {
     "q": {
      "standard": "Once temperatures have settled, what sets the air's temperature rise through the box? Explain mode shows it under ΔT front→back.",
      "novice": "Once temperatures stop changing, what decides how much hotter the air is at the back than at the front?"
     },
     "a": {
      "standard": "ΔT = DC / (ṁ·cp): the heat, which is the DC power, divided by the mass flow of air times air's heat capacity. More watts or less air means a larger rise.",
      "novice": "How much heat the server makes, and how much air the fans push through. More heat or less air means hotter air out the back."
     },
     "cite": [
      "DellPowerEdgeR760Thermal/backend/tests/test_engine.py::test_heat_balance_at_steady_state"
     ]
    },
    {
     "q": {
      "standard": "Before the inlet step in the fan-feedback run, the wall reads about 715 W and DC about 674 W. What is the supply efficiency, and where do the other watts go?",
      "novice": "Before the room heats up, the wall power reads about 715 watts but the parts inside add up to about 674 watts. Where does the difference go?"
     },
     "a": {
      "standard": "About 94%: 674 ÷ 715. The remaining 41 W or so is lost in the power supplies as heat. Explain mode gives the rule as P_wall = P_dc / η, with η read off the supplies' load curve.",
      "novice": "Into the power supplies themselves. They turn wall electricity into the kind the parts use and waste about 6% doing it, around 41 watts here, which also becomes heat."
     },
     "cite": [
      "DellPowerEdgeR760Thermal/backend/tests/test_engine.py::test_wall_power_is_dc_over_efficiency"
     ]
    }
   ],
   "pins": [],
   "lab": {
    "twin": "DellPowerEdgeR760Thermal",
    "port": 5203,
    "id": "psu-sweet-spot",
    "title": "Find the PSU sweet spot",
    "difficulty": 1,
    "label": "Open the lab: Find the PSU sweet spot",
    "goal": {
     "standard": "Size the R760's power supplies to the load the build actually carries: keep the redundant pair, keep real work coming out, and push the mean supply efficiency up. The module's feedback loop is the trap — the fans are load too, so a hotter build moves the efficiency point you were aiming at.",
     "novice": "Pick power supplies that match what this server really draws. Keep two of them, so one can fail and the server stays up, and keep the server doing real work. Then waste as little electricity in the supplies as you can. The catch is the one from this module: the fans are part of the load, so cooling the machine changes the number you are trying to improve."
    },
    "lever": {
     "standard": "The lever is the gap between the supplies' rating and the peak the build reaches, read against the efficiency curve in Explain mode.",
     "novice": "The thing to change is how big the supplies are compared with the most the server ever draws. Explain mode shows the curve you are sitting on."
    },
    "how": {
     "standard": "Open the Labs tab in the app, pick this lab, read its goal and constraints, and build the scenario with the controls this module already used. Run and grade replays the same pure engine and scores the trace: every constraint is measured from the trace, not taken on trust, so an idle build cannot pass. Thresholds and scores are illustrative.",
     "novice": "In the app, open the tab called Labs and choose this lab. It states a goal and some rules. Set the controls the way you think will work, then press Run and grade. The app checks what actually happened in the run, so you cannot pass by doing nothing. Change one setting at a time and grade again. The pass marks are made up for teaching, not measurements."
    },
    "cite": [
     "DellPowerEdgeR760Thermal/backend/tests/test_labs.py::test_lab_invariants",
     "DellPowerEdgeR760Thermal/backend/tests/test_labs.py::test_there_are_three_labs_of_rising_difficulty"
    ]
   },
   "bridge": {
    "text": {
     "standard": "One R760 moves its heat with air. An eight-GPU server draws around 11 kW in the next module's twin (illustrative), and at that density air starts to run out. The next module scales the box up.",
     "novice": "One ordinary server can be cooled with fans. Servers packed with GPUs make far more heat. Next, see what changes when a box holds eight GPUs, then a whole rack holds seventy-two."
    },
    "next": "M4"
   },
   "scenarioPins": [
    {
     "twin": "DellPowerEdgeR760Thermal",
     "scenario": "fan-feedback",
     "step": 179,
     "field": "acPowerW",
     "value": 715
    },
    {
     "twin": "DellPowerEdgeR760Thermal",
     "scenario": "fan-feedback",
     "step": 179,
     "field": "dcPowerW",
     "value": 674
    },
    {
     "twin": "DellPowerEdgeR760Thermal",
     "scenario": "fan-feedback",
     "step": 179,
     "field": "fanPowerW",
     "value": 16
    },
    {
     "twin": "DellPowerEdgeR760Thermal",
     "scenario": "fan-feedback",
     "step": -1,
     "field": "fanPowerW",
     "value": 65
    },
    {
     "twin": "DellPowerEdgeR760Thermal",
     "scenario": "fan-feedback",
     "step": -1,
     "field": "acPowerW",
     "value": 767
    },
    {
     "twin": "DellPowerEdgeR760Thermal",
     "scenario": "kill-a-fan",
     "step": -1,
     "field": "fanPowerW",
     "value": 23
    },
    {
     "twin": "DellPowerEdgeR760Thermal",
     "scenario": "kill-a-fan",
     "step": -1,
     "field": "airflowCfm",
     "value": 71
    }
   ]
  },
  {
   "id": "M4",
   "title": "Eight GPUs, then seventy-two",
   "core": true,
   "idea": {
    "standard": "How many GPUs can address each other's memory over NVLink, and where that group's wall sits, is the design decision.",
    "novice": "Fast links between GPUs can make many of them act as one big GPU. How big that group can get, one box or one whole rack, shapes everything else."
   },
   "prereqs": [
    "M2",
    "M3"
   ],
   "background": {
    "standard": "A server boots its host first, and fans are part of the load. NVLink is NVIDIA's GPU-to-GPU link, NVSwitch is the switch chip for it, and a domain is the set of GPUs that can read and write each other's memory over it.",
    "novice": "A server starts its ordinary computer first, and its fans are part of what it has to power. NVIDIA calls its fast GPU-to-GPU link NVLink, and calls a group of GPUs joined by it a domain."
   },
   "objectives": [
    {
     "standard": "Say how the NVLink domain comes into being, and what decides its size.",
     "novice": "Say how the group of joined GPUs (the NVLink domain) comes into being."
    },
    {
     "standard": "Locate the domain wall: the chassis for the XE9680, the rack for the XE9712.",
     "novice": "Say where the group ends: the metal box for the XE9680, the whole rack for the XE9712."
    },
    {
     "standard": "Explain why the rack proves its coolant flow before it powers any silicon, and compare what air and liquid cooling cost.",
     "novice": "Explain why the rack starts its cooling liquid before its chips, and compare what fans and pumps cost in electricity."
    }
   ],
   "entries": [
    {
     "twin": "DellPowerEdgeXE9680",
     "port": 5201,
     "trace": "poweron",
     "pageTitle": "PowerEdge XE9680 Inside",
     "name": "PowerEdge XE9680 (eight GPUs)",
     "links": [
      {
       "kind": "tour",
       "id": "domain-stops-at-eight",
       "label": "Guided tour, where the domain stops at eight",
       "lockedLabel": "Guided tour, at the domain",
       "how": {
        "standard": "The link opens the tour part-way through. Press Previous to reach the first beat, where the terms are introduced.",
        "novice": "The link opens the tour in the middle. Press Previous until the first beat and watch it through; the earlier beats explain the words this one uses."
       }
      },
      {
       "kind": "phase",
       "value": "fuse",
       "label": "Power-on trace, at the fuse",
       "how": {
        "standard": "The link counts steps from zero; the twin's Telemetry panel counts from one, and so do the answers below.",
        "novice": "The model counts its steps from one, and the answers below use the numbers on its screen."
       },
       "lockedLabel": "Power-on trace, at the domain"
      },
      {
       "kind": "phase",
       "value": "fabric",
       "label": {
        "standard": "Power-on trace, as the NICs join",
        "novice": "Power-on trace, as the network cards join"
       }
      }
     ]
    },
    {
     "twin": "DellPowerEdgeXE9712",
     "port": 5181,
     "trace": "poweron",
     "pageTitle": "PowerEdge XE9712 Inside",
     "name": {
      "standard": "PowerEdge XE9712 (GB200 NVL72 rack)",
      "novice": "PowerEdge XE9712 (a whole rack of 72 GPUs)"
     },
     "note": {
      "standard": "The same question one size up. The XE9680 ends its domain at the sheet metal; this twin moves the wall out to the rack, so the fuse joins 72 GPUs instead of 8 — and the cooling has to change with it, which is the second thing to watch here.",
      "novice": "The same question, one size bigger. In the box above, the group of joined GPUs stops at the edge of the metal case. Here the whole rack is the machine, so the group is 72 — and the cooling has to change to match, which is the other thing to watch."
     },
     "links": [
      {
       "kind": "tour",
       "id": "atomic-fuse",
       "label": "Guided tour, at the atomic fuse",
       "lockedLabel": "Guided tour, at the domain",
       "how": {
        "standard": "The link opens the tour part-way through. Press Previous to reach the first beat, where the terms are introduced.",
        "novice": "The link opens the tour in the middle. Press Previous until the first beat and watch it through; the earlier beats explain the words this one uses."
       }
      },
      {
       "kind": "tour",
       "id": "liquid-before-silicon",
       "label": "Guided tour, at liquid before silicon"
      },
      {
       "kind": "phase",
       "value": "fused",
       "label": "Power-on trace, at the fuse",
       "lockedLabel": "Power-on trace, at the domain"
      }
     ]
    },
    {
     "twin": "PhysicsCompute",
     "port": 5205,
     "pageTitle": "AI Compute &middot; Power &amp; Thermal Simulator",
     "name": "AI compute physics",
     "links": [
      {
       "kind": "scenario",
       "id": "air-vs-liquid",
       "title": "Air vs liquid",
       "label": "Air vs liquid",
       "how": {
        "standard": "Pick a faster speed and let both runs settle. Read the cooling overhead row in the A/B panel above the instruments: the share of electricity spent on fans and pumps rather than on computing, for the rack and for one XE9680 with 1,000 W GPUs.",
        "novice": "Pick a faster speed and wait for the numbers to settle. Find the row called cooling overhead in the A/B panel: it is the share of the electricity that goes on fans and pumps instead of computing. Compare the rack with the single box beside it."
       }
      }
     ],
     "note": {
      "standard": "The same two machines, running instead of booting. Moving the wall from the chassis to the rack also moves the heat: 72 GPUs are nine XE9680s' worth of fan walls — more than one rack holds at 6U apiece — against a single pumped loop. It is a comparison of cooling per GPU, not a swap a site could make rack for rack. This app is a separate physics model with its own illustrative numbers.",
      "novice": "The same two machines, now running instead of starting up. Seventy-two GPUs is nine boxes' worth of fans — more than a single rack could hold — against one rack cooled by pumped liquid. It is a comparison of what cooling each GPU costs, not two things you could swap. This is a simulator, not a tour, and its numbers are its own."
     }
    }
   ],
   "predict": {
    "q": {
     "standard": "An XE9712 rack brings up 72 GPUs, four to a tray. As the NVLink links train, does the count of GPUs in the NVLink domain climb gradually (4, 8, 12 and so on) or jump?",
     "novice": "A rack has 72 GPUs, four to a tray (a drawer that slides into the rack), that are about to be joined into one group. Do they join a few at a time, or all at once?"
    },
    "options": [
     {
      "standard": "It climbs a tray at a time",
      "novice": "It climbs a few GPUs at a time, tray by tray"
     },
     {
      "standard": "It jumps from 0 to 72 in one step",
      "novice": "It jumps from 0 to 72 all at once"
     },
     {
      "standard": "It stops at 8, one server's worth",
      "novice": "It stops at 8"
     }
    ],
    "answer": 1,
    "reveal": {
     "standard": "It jumps from 0 to 72 in one step, at the phase the twin labels one NVLink domain. The domain is a partition that the fabric manager activates only after every link has trained, so the counter is a membership count, not a tally of trained links. This twin models the rack as a single 72-GPU partition, which is why it never shows a value in between; the failure stop below comes back to that choice.",
     "novice": "All at once. The count is 0 right up until the moment it is 72. The links are tested one by one, but the group is only switched on by the rack's management software once the last link has passed. This model treats the rack as one group of 72, so it never shows a half-joined state."
    },
    "cite": [
     "DellPowerEdgeXE9712/backend/tests/test_engine.py::test_fuse_joins_all_72_gpus_at_once"
    ]
   },
   "checks": [
    {
     "q": {
      "standard": "In the XE9680, which comes first: the eight NICs (network cards) joining the fabric, or the NVLink fuse?",
      "novice": "In the eight-GPU box, which happens first: the eight network cards joining the network, or the eight GPUs joining each other?"
     },
     "a": {
      "standard": "The fuse. On the twin's screen the domain reaches 8 at step 5 of 7 while no NIC is up, and the NICs reach 8 at step 6. The domain never grows past 8: NVLink stays inside the box, and Ethernet carries everything beyond it.",
      "novice": "The GPUs join each other first. On the screen the group reaches 8 at step 5 of 7 while no network card is up, and the network cards come up at step 6. The group never grows past 8, because the fast links stop at the edge of the box."
     },
     "cite": [
      "DellPowerEdgeXE9680/backend/tests/test_engine.py::test_the_fuse_is_atomic_and_the_domain_stops_at_eight",
      "DellPowerEdgeXE9680/backend/tests/test_engine.py::test_one_nic_per_gpu_joins_the_fabric_after_the_fuse"
     ]
    },
    {
     "q": {
      "standard": "What does the XE9712 do before any tray boots, and why?",
      "novice": "What does the big rack do before any of its trays of GPUs switch on, and why?"
     },
     "a": {
      "standard": "It primes the coolant loop and verifies leaks and flow on every branch — step 3 of 8 on screen, with the compute trays powering on at step 4. A cold plate with no flow overheats almost at once, so the loop is proven before any silicon draws power. The nominal trace states the check but shows no count; the branches-verified counter (17 or 18 of 18) appears only in the coolant-fault trace further down this page, which is where the number 18 comes from.",
      "novice": "It starts the cooling liquid flowing and checks every branch for leaks and flow — step 3 of 8 on the screen; the computing trays switch on at step 4. (The trays are the drawers of GPUs, not the power shelves at the top of the rack, which came on at step 2.) A chip with no liquid flowing over it overheats almost at once, so the cooling is proven first. The screen does not count the branches here; the counter that does, 18 of 18, shows up in the leak trace further down this page."
     },
     "cite": [
      "DellPowerEdgeXE9712/backend/tests/test_engine.py::test_coolant_flows_before_any_silicon"
     ]
    },
    {
     "q": {
      "standard": "Which stage does playback dwell on longest in each twin, and why do they differ?",
      "novice": "Which step does each model linger on longest, and why are they different?"
     },
     "a": {
      "standard": "XE9680: the eight GPUs waking, which trains the high-bandwidth memory on each of them. XE9712: the NVLink links training over the rack's 5,000 copper cables. Each twin says outright, in the tour beat and in the step's own caption, that its stage is the long one; both screens say only that longer real-world stages stay on screen longer. The weight behind that behaviour is in the trace data rather than on the screen (a cycle cost of 5, a relative weight and not seconds; the choice is illustrative). The XE9680's fuse runs over board traces and needs no cable training.",
      "novice": "In the eight-GPU box it is the step where the GPUs wake and test their own memory. In the rack it is the step where the fast links are tested over thousands of copper cables at the back. The box has no such cables: its GPUs are joined by wiring on a circuit board, so there is nothing to test."
     },
     "cite": [
      "DellPowerEdgeXE9680/backend/tests/test_engine.py::test_gpu_init_is_the_longest_stage",
      "DellPowerEdgeXE9712/backend/tests/test_engine.py::test_fabric_training_is_the_longest_stage"
     ]
    },
    {
     "q": {
      "standard": "In the physics app's Air vs liquid run, what share of electricity goes on cooling for the rack, and for the air-cooled XE9680 beside it?",
      "novice": "In the simulator, what share of the electricity goes on cooling for the liquid-cooled rack, and for the fan-cooled box beside it?"
     },
     "a": {
      "standard": "About 1.4% for the rack (pumps plus the small tray fans) against about 15% for the B200-class XE9680 with its fans at full speed. Both figures count only the cooling inside the enclosure: the rack's 1.4% is its in-rack pump pair, and the facility loop that finally rejects that heat is outside the number, exactly as the room's chiller is outside the box's 15%. Whole-site figures (PUE) narrow the gap to something nearer three than ten. Both figures are the app's estimates.",
      "novice": "About 1.4% for the rack and about 15% for the box. Pumping liquid is far cheaper than blowing enough air, which is the fan cube law from the last module again. Both numbers count only the cooling inside the machine; the building's own chillers and pumps, which take the heat the rest of the way outside, are not in either figure, and counting them narrows the gap a lot. Both numbers are estimates."
     },
     "cite": [
      "PhysicsCompute/backend/tests/test_engine.py::test_both_sides_of_the_overhead_comparison_count_their_fans",
      "PhysicsCompute/backend/tests/test_engine.py::test_liquid_cooling_overhead_beats_air"
     ]
    }
   ],
   "pins": [
    {
     "twin": "DellPowerEdgeXE9712",
     "step": 5,
     "field": "gpus_in_domain",
     "value": 0
    },
    {
     "twin": "DellPowerEdgeXE9712",
     "step": 6,
     "field": "gpus_in_domain",
     "value": 72
    },
    {
     "twin": "DellPowerEdgeXE9712",
     "step": 2,
     "field": "phase",
     "value": "coolant"
    },
    {
     "twin": "DellPowerEdgeXE9680",
     "step": 4,
     "field": "gpus_in_domain",
     "value": 8
    },
    {
     "twin": "DellPowerEdgeXE9680",
     "step": 4,
     "field": "nics_up",
     "value": 0
    },
    {
     "twin": "DellPowerEdgeXE9680",
     "step": 5,
     "field": "nics_up",
     "value": 8
    },
    {
     "twin": "DellPowerEdgeXE9712",
     "step": 3,
     "field": "phase",
     "value": "trayboot"
    },
    {
     "twin": "DellPowerEdgeXE9712",
     "step": 5,
     "field": "cycle_cost",
     "value": 5
    },
    {
     "twin": "DellPowerEdgeXE9680",
     "step": 3,
     "field": "cycle_cost",
     "value": 5
    }
   ],
   "lab": {
    "twin": "PhysicsCompute",
    "port": 5205,
    "id": "worst-seat",
    "title": "Keep the worst seat cool",
    "difficulty": 1,
    "label": "Open the lab: Keep the worst seat cool",
    "goal": {
     "standard": "Eight PCIe cards in a warm aisle, each riser breathing air the slots ahead of it have already warmed. Keep all eight cards, deliver the work, and hold the hottest slot under the throttle line for the whole run — the positional throttle order this module watched, now as a thing you have to beat.",
     "novice": "Eight accelerator cards sit in a row, and each one breathes air the cards in front of it have already heated. So the last card is the hottest and slows down first. Keep all eight cards, keep the work coming, and stop that last card from ever getting hot enough to slow down."
    },
    "lever": {
     "standard": "Airflow and inlet temperature move every seat at once; the per-card power dial moves the preheat the downstream seats inherit.",
     "novice": "Two things help every card: more air, or cooler air. A third helps only the cards behind: turning the front cards down a little."
    },
    "how": {
     "standard": "Open the Labs tab in the app, pick this lab, read its goal and constraints, and build the scenario with the controls this module already used. Run and grade replays the same pure engine and scores the trace: every constraint is measured from the trace, not taken on trust, so an idle build cannot pass. Thresholds and scores are illustrative.",
     "novice": "In the app, open the tab called Labs and choose this lab. It states a goal and some rules. Set the controls the way you think will work, then press Run and grade. The app checks what actually happened in the run, so you cannot pass by doing nothing. Change one setting at a time and grade again. The pass marks are made up for teaching, not measurements."
    },
    "cite": [
     "PhysicsCompute/backend/tests/test_labs.py::test_lab_invariants",
     "PhysicsCompute/backend/tests/test_labs.py::test_there_are_three_labs_one_per_machine"
    ]
   },
   "bridge": {
    "text": {
     "standard": "The XE9712 will not power a tray until its coolant loop has proved itself. The next module is that loop, seen from the cooling side.",
     "novice": "The big rack will not switch on its GPUs until the cooling liquid is flowing. Next, look at the cooling loop itself."
    },
    "next": "M5"
   },
   "failures": [
    {
     "twin": "DellPowerEdgeXE9712",
     "port": 5181,
     "trace": "poweron",
     "name": {
      "standard": "XE9712: a coolant leak under full load",
      "novice": "XE9712: a coolant leak while the rack is working"
     },
     "scenario": "coolant-fault",
     "at": {
      "kind": "phase",
      "value": "leak"
     },
     "label": "Coolant-fault trace, paused on the leak under load",
     "q": {
      "standard": "The rack is running with all 72 GPUs fused into one NVLink domain, and this site schedules the rack only as a single 72-GPU partition. A cold-plate leak sensor trips on one compute tray and that tray's management controller cuts its four GPUs from the busbar. The other 68 are healthy, powered and cooled. What does the GPUs-in-domain counter read on the next step?",
      "novice": "A rack of 72 GPUs is working as one giant GPU, and this site only ever uses it as one group of 72. One tray of four springs a coolant leak and is switched off. The other 68 are fine. How many GPUs are still joined together as one?"
     },
     "options": [
      {
       "standard": "68: the healthy GPUs carry on as a smaller domain",
       "novice": "68: the healthy ones carry on as a smaller group"
      },
      {
       "standard": "72: the domain rides through it",
       "novice": "72: the group rides through it"
      },
      {
       "standard": "0: the partition ends",
       "novice": "0: the group ends"
      }
     ],
     "answer": 2,
     "a": {
      "standard": "The counter reads 0 while 68 of 72 GPUs stay powered. The twin models one 72-GPU partition, so losing a tray ends it; the job fails on its next access to the lost tray's memory and restarts from its last checkpoint. Power moves first: rack watts fall on the step the sensor trips, and the hottest GPU never exceeds its healthy full-load 70 °C. Earlier in the trace, when 17 of 18 branches verify before GPU init, no GPU is powered at all. That rack-wide hold is the modelled site's one-domain policy, not a hardware interlock: NVIDIA's guide to its partition software (IMEX) no longer requires a full quorum, so a real site can re-form a 68-GPU partition. A tray has no valve of its own; its quick disconnects seal when a technician unseats it. Figures are illustrative.",
      "novice": "Zero. The 72 GPUs were joined as one group, and in this model the group either has all 72 or does not exist, so losing one tray ends it even though 68 GPUs are still switched on. The running job stops and restarts from its last save point. Power drops first: the leaking tray is cut off at once, so the chips never get hotter than normal. A real site could choose to regroup the 68 survivors; this model keeps the rule simple and says so."
     },
     "cite": [
      "DellPowerEdgeXE9712/backend/tests/test_scenarios.py::test_the_domain_is_only_ever_0_or_72_never_68",
      "DellPowerEdgeXE9712/backend/tests/test_scenarios.py::test_power_drops_before_temperature_rises",
      "DellPowerEdgeXE9712/backend/tests/test_scenarios.py::test_no_gpu_draws_power_without_verified_flow",
      "DellPowerEdgeXE9712/backend/tests/test_scenarios.py::test_the_bring_up_hold_is_rack_wide"
     ],
     "pins": [
      {
       "step": 12,
       "field": "gpusInDomain",
       "value": 0
      },
      {
       "step": 12,
       "field": "gpusPowered",
       "value": 68
      },
      {
       "step": 3,
       "field": "branchesVerified",
       "value": 17
      },
      {
       "step": 3,
       "field": "gpusPowered",
       "value": 0
      },
      {
       "agg": "max",
       "field": "gpuTempC",
       "value": 70
      }
     ],
     "how": {
      "standard": "The trace holds two faults. The link lands on the second, the leak under full load, step 13 of 15 on screen. The first is a branch that fails flow verification at bring-up, step 4 of 15; it delays the start rather than preventing it — the tray is isolated and reseated, all 18 branches re-verify at step 7, and the rack is accepting jobs by step 12. Two terms in the question: a cold plate is the liquid-cooled metal block bolted onto a chip, and the busbar is the shared DC power rail running down the back of the rack.",
      "novice": "This trace has two coolant faults in it. The link opens on the second, the leak while the rack is working, which is the one the question asks about. The first is near the start: one branch fails its flow check, the tray is pulled and resealed, and the rack then starts normally — it is delayed, not stopped."
     }
    }
   ],
   "scenarioPins": [
    {
     "twin": "PhysicsCompute",
     "scenario": "air-vs-liquid",
     "step": -1,
     "field": "coolingOverheadPct",
     "value": 1.4,
     "tol": 0.05
    }
   ]
  },
  {
   "id": "M5",
   "title": "Liquid: heat in equals heat out",
   "core": true,
   "idea": {
    "standard": "A cooling loop is a device for making three numbers equal: the heat the IT makes, the heat the rack coolant carries, and the heat the building water takes away. Coordination decides what gives when it cannot.",
    "novice": "Every watt of heat the computers make has to be carried off by the rack's coolant and then handed to the building's water, exactly. When the water can't keep up, something has to slow down, and it matters who decides."
   },
   "prereqs": [
    "M3",
    "M4"
   ],
   "background": {
    "standard": "Air's temperature rise is heat divided by mass flow times heat capacity, and the XE9712 proves coolant flow before it powers silicon. Three parts recur here: a cold plate is the liquid-cooled block bolted to a chip, the CDU (coolant distribution unit) is the pump and heat-exchanger box, and the rear door (eRDHx on the drawing) is a water coil that catches the heat left in the air. Two forms of one law run through this module: how the heat is caught (cold plates plus air equals the IT load) and where it goes next (the IT heat, the rack loop's heat and the building loop's heat are one number).",
    "novice": "From the last two modules: moving heat takes flow, and the big rack starts its liquid before its chips. Three parts come up here. A cold plate is a metal block with liquid running through it, bolted onto a chip. The CDU is the box with the pumps. The rear door (labelled eRDHx on the drawing) is a radiator on the back of the rack that catches whatever heat escapes into the air. One law turns up twice here: how the heat is caught (the part the liquid takes plus the part the air takes is all of it) and where it goes next (what the computers make, what the rack's liquid carries and what the building's water takes away are the same amount)."
   },
   "objectives": [
    {
     "standard": "State the heat balance: heat captured at the cold plates plus heat captured from the air equals the IT load, exactly.",
     "novice": "Say where the heat goes: the part the liquid takes plus the part the air takes always adds up to all the heat the computers make."
    },
    {
     "standard": "Explain why flow is established and verified before any heat arrives.",
     "novice": "Explain why the liquid has to be flowing, and checked, before any computer is switched on."
    },
    {
     "standard": "Compare what a rack controller does on a warm-water day with what happens without one.",
     "novice": "Compare a warm-water day with a controller in charge against one where each group of computers looks after itself."
    }
   ],
   "entries": [
    {
     "twin": "DellIR7000",
     "port": 5182,
     "trace": "thermal",
     "name": "IR7000 liquid-cooled rack",
     "pageTitle": "IR7000 + PowerCool Inside",
     "links": [
      {
       "kind": "tour",
       "id": "heat-balance",
       "label": "Guided tour, at the heat balance",
       "how": {
        "standard": "The link opens the tour at beat 5 of 8, the heat balance. Press Previous once for the beat that says why every branch is checked one by one and which stage is longest, again for the order flow comes in, and on to the first beat for the parts of the loop.",
        "novice": "The link opens the tour in the middle, at beat 5 of 8. Press Previous once to hear why every pipe is checked one at a time, and keep pressing back to the first beat; the earlier beats explain the parts."
       }
      },
      {
       "kind": "phase",
       "value": "verify",
       "label": "Thermal trace, at leak and flow verification",
       "lockedLabel": "Thermal trace, at the stage before any load"
      },
      {
       "kind": "phase",
       "value": "steady",
       "label": "Thermal trace, at steady state"
      }
     ]
    },
    {
     "twin": "PhysicsCDU",
     "port": 5216,
     "name": "Coolant distribution unit physics",
     "pageTitle": "PowerCool CDU Physics Simulator",
     "links": [
      {
       "kind": "scenario",
       "id": "warm-water-day",
       "title": "Warm water day (coordinated)",
       "label": "Warm water day (coordinated)",
       "how": {
        "standard": "The run starts at ×1 and the water warms at t+420 s, so pick a faster speed — but pause before t+420 if you want the before reading, since at ×60 that moment passes between frames and there is no scrubber. Two things look like events and are not: the cap already sits near 98% in the first minutes because this build is a 240 kW rack on a 220 kW-class CDU, not because it is still warming up; and the facility row reads supply → return, where the return is the supply plus the exchanger's 6 K design rise, so 17.0 → 23.0 °C before the event is normal. The number that steps at t+420 is the supply. When it settles, read banks online and heat moved, then run the other scenario and compare.",
        "novice": "The run starts slowly and nothing happens for the first seven minutes of model time, so pick a faster speed — but pause before the seven-minute mark if you want to read the before figure, because at the fastest speed that moment slips past and you cannot go back. Two things look like the event and are not. The speed limit already reads about 98% early on: this rack makes a little more heat than the box is built for, so it is trimmed from the start. And the building-water row shows two temperatures, the water going in and the same water coming back six degrees warmer, so 17.0 → 23.0 °C is the quiet state, not the event. When it settles, read two rows: banks online and heat moved. Then run the other link and compare."
       }
      },
      {
       "kind": "scenario",
       "id": "warm-water-panic",
       "title": "Warm water day (panic)",
       "label": {
        "standard": "Warm water day (panic): the uncoordinated run",
        "novice": "Warm water day (panic): each group for itself"
       }
      }
     ],
     "note": {
      "standard": "IR7000 showed the balance holding when everything works. This simulator takes a different, newer CDU (the PowerCool C7000, 220 kW class) with its own illustrative constants and six tray banks, so its flows and kilowatts do not match the IR7000 twin's. What it adds is the thermodynamics of the building-water side, which the IR7000 draws but never measures: the facility loop's own flow and temperature rise, the heat exchanger's toll between the two loops, and a rack controller (the IRC) that decides what gives when the water cannot carry the heat. Only one kilowatt figure is on screen, heat moved; the two loops appear as a flow and a temperature rise each, and Explain mode in the top bar writes out the rule tying all three together.",
      "novice": "The CDU is the pump-and-heat-exchanger box from the rack you just toured. This simulator looks inside a newer one, and its numbers are its own, so they will not match the first model's. What is new is the building's water measured rather than just drawn — how much of it is flowing and how much warmer it leaves — and a controller that decides who slows down when that water gets too warm. Only one reading is in kilowatts (heat moved); each liquid shows instead as a flow and a temperature rise. Explain mode, at the top of the page, says in words how the three fit together."
     }
    }
   ],
   "predict": {
    "q": {
     "standard": "Building water arrives 6 °C warmer, and the loop needs about 15% of the rack's load shed to absorb it. In the run with no coordination, where each bank of trays protects only itself, how much does the rack actually shed?",
     "novice": "The water from the building arrives six degrees warmer. To cope, the rack has to give up about a seventh of its work. In the version where each group of computers looks after only itself, how much work does the rack actually lose?"
    },
    "options": [
     "About a seventh — what the warm water required",
     "About half — far more than the warm water required",
     "Nothing — they ride it out"
    ],
    "answer": 1,
    "reveal": {
     "standard": "About half. The coordinated run caps every bank to about 80%, keeps all six online and settles near 205 kW. The uncoordinated run trips three of six banks, five seconds apart, and settles at 120 kW — roughly half the work, where about 15% was all the warm water demanded. The loop's lag keeps the survivors hot after the first trip, so the trips cascade. Read the size of that gap as the model's worst case rather than a measurement: in this simulator a bank is either at full speed or tripped off, and the app's own footnote says real trays slow their clocks before a hard trip. Its event log adds that all six banks share one silicon reading here, with trip timers staggered five seconds apart, so bank 1 always goes first. Figures are the app's estimates.",
     "novice": "About half. With a controller, everyone slows a little (to about 80%), nothing shuts down, and all six groups stay on. Without one, three of the six shut off one after another and half the work is lost, when slowing down by about a seventh would have been enough. Two cautions the app itself gives: in this model a group is either at full speed or off, while real computers slow themselves down first, and the order the groups fail in is set by the model rather than worked out, so treat the gap as the worst case and the lesson as the shape."
    },
    "cite": [
     "PhysicsCDU/backend/tests/test_engine.py::test_acceptance_warm_water_day_coordinated_sheds_gracefully",
     "PhysicsCDU/backend/tests/test_engine.py::test_acceptance_warm_water_day_uncoordinated_cascades"
    ]
   },
   "checks": [
    {
     "q": {
      "standard": "At IR7000 steady state, what share of the 264 kW is captured directly at the cold plates, and where does the rest go?",
      "novice": "When the rack is running flat out at 264 kW, how much of the heat does the liquid on the chips take, and where does the rest go?"
     },
     "a": {
      "standard": "240 kW, about 91%, at the cold plates. The other 24 kW goes into the air, where the rear-door coil captures it into the same loop, so all 264 kW ends up in facility water. The two terms sum exactly on every step.",
      "novice": "240 kW, about 91%. The other 24 kW escapes into the air, and the radiator in the rear door catches it, so in the end all of it leaves in the building's water. The two parts always add up exactly."
     },
     "cite": [
      "DellIR7000/backend/tests/test_engine.py::test_heat_balance_holds_on_every_step",
      "DellIR7000/backend/tests/test_engine.py::test_liquid_carries_the_overwhelming_share"
     ]
    },
    {
     "q": {
      "standard": "Why is coolant already flowing at 80 L/min while the IT load is still zero?",
      "novice": "Why is the liquid already flowing (80 litres a minute) while the computers are still switched off?"
     },
     "a": {
      "standard": "Because the loop is proven before it is loaded. The pumps run and every branch is leak- and flow-verified with no heat present, since a cold plate without flow overheats almost at once and a blocked branch hides inside a whole-rack flow reading. Only then may the payload power on; the trace asserts flow above zero strictly before the first IT watt.",
      "novice": "Because the loop must prove it can carry heat away before any computer is allowed to make heat. A chip with no liquid flowing overheats in seconds, and one blocked branch would cook one server while the total flow still looked fine. So every branch is checked first, with nothing switched on."
     },
     "cite": [
      "DellIR7000/backend/tests/test_engine.py::test_flow_before_heat"
     ]
    },
    {
     "q": {
      "standard": "Which IR7000 stage does playback dwell on longest?",
      "novice": "Which step does the rack model linger on longest?"
     },
     "a": {
      "standard": "Leak and flow verification, the per-branch check. The page itself only says the stage dwells longest; the multiplier is in the trace, where it carries a cycle cost of 5 against a normal step's 1 — a relative weight, not seconds, and not a readout on screen.",
      "novice": "The leak and flow check, because every branch is tested one by one. The page tells you it stays on screen longer than the others, but not by how much: the model's own data holds that number, and it is five times a normal step."
     },
     "cite": [
      "DellIR7000/backend/tests/test_engine.py::test_verification_is_the_longest_stage"
     ]
    },
    {
     "q": {
      "standard": "In the CDU simulator, which three quantities are equal at every step?",
      "novice": "In the CDU simulator, which three amounts of heat always match?"
     },
     "a": {
      "standard": "The IT heat, the heat the secondary (rack) loop carries, and the heat the primary (facility) loop takes away. Each loop's figure is its flow times the coolant's heat capacity times its temperature rise, and the instruments show both pairs — but they hold the identity in opposite ways: the rack loop runs at a fixed 340 L/min and lets its rise move, while a valve on the facility side holds that loop's rise at its 6 K design figure and moves the flow instead. Watch the facility flow row, not its temperatures, when the load changes.",
      "novice": "The heat the computers make, the heat the rack's liquid carries, and the heat the building's water takes away. Each liquid's share is how fast it flows times how much warmer it comes back. The two behave differently on screen: the rack's liquid flows at a steady rate and comes back hotter or cooler, while a valve keeps the building's water always six degrees warmer on the way out and changes how much of it flows instead. So when the load moves, watch the building-water flow, not its temperatures."
     },
     "cite": [
      "PhysicsCDU/backend/tests/test_engine.py::test_heat_balance_both_loops_every_tick"
     ]
    }
   ],
   "pins": [
    {
     "twin": "DellIR7000",
     "step": 7,
     "field": "it_load_watts",
     "value": 264000
    },
    {
     "twin": "DellIR7000",
     "step": 7,
     "field": "liquid_watts",
     "value": 240000
    },
    {
     "twin": "DellIR7000",
     "step": 2,
     "field": "it_load_watts",
     "value": 0
    },
    {
     "twin": "DellIR7000",
     "step": 2,
     "field": "flow_lpm",
     "value": 80
    },
    {
     "twin": "DellIR7000",
     "step": 3,
     "field": "cycle_cost",
     "value": 5
    },
    {
     "twin": "DellIR7000",
     "step": 7,
     "field": "air_watts",
     "value": 24000
    }
   ],
   "lab": {
    "twin": "PhysicsCDU",
    "port": 5216,
    "id": "full-rack-lean-pumps",
    "title": "Full rack, leanest pumps",
    "difficulty": 1,
    "label": "Open the lab: Full rack, leanest pumps",
    "goal": {
     "standard": "A full rack against a CDU near its nameplate: run every bank flat out with no capping and the silicon under the target, then spend as little pump power as you can doing it. The heat identity from this module is what makes it a real trade — the load is pinned by the work floor, so flow is the only free variable left.",
     "novice": "The rack is full and the cooling unit is near its limit. Keep all the banks running at full speed, with the chips cool enough that nothing gets slowed down — and then use as little electricity in the pumps as you can. Because the heat has to go somewhere, the only thing you can really change is how fast the coolant moves."
    },
    "lever": {
     "standard": "Pump power goes with speed cubed, so the last few litres a minute are the expensive ones; the approach temperature and half the loop rise are what buying them fixes.",
     "novice": "Pumps get expensive very fast: twice the speed costs about eight times the electricity. So find the slowest flow that still keeps the chips cool enough."
    },
    "how": {
     "standard": "Open the Labs tab in the app, pick this lab, read its goal and constraints, and build the scenario with the controls this module already used. Run and grade replays the same pure engine and scores the trace: every constraint is measured from the trace, not taken on trust, so an idle build cannot pass. Thresholds and scores are illustrative.",
     "novice": "In the app, open the tab called Labs and choose this lab. It states a goal and some rules. Set the controls the way you think will work, then press Run and grade. The app checks what actually happened in the run, so you cannot pass by doing nothing. Change one setting at a time and grade again. The pass marks are made up for teaching, not measurements."
    },
    "cite": [
     "PhysicsCDU/backend/tests/test_labs.py::test_lab_invariants",
     "PhysicsCDU/backend/tests/test_labs.py::test_there_are_three_labs_of_rising_difficulty"
    ]
   },
   "bridge": {
    "text": {
     "standard": "The rack is powered, fused and cooled, and now it wants data. The next module starts with the arithmetic every storage system pays.",
     "novice": "The machines are on and cool. Now they need data. Next: what it really costs to save something to disk."
    },
    "next": "M6"
   },
   "scenarioPins": [
    {
     "twin": "PhysicsCDU",
     "scenario": "warm-water-day",
     "step": -1,
     "field": "groupsOnline",
     "value": 6
    },
    {
     "twin": "PhysicsCDU",
     "scenario": "warm-water-day",
     "step": -1,
     "field": "heatRemovedKw",
     "value": 205
    },
    {
     "twin": "PhysicsCDU",
     "scenario": "warm-water-panic",
     "step": -1,
     "field": "trips",
     "value": 3
    },
    {
     "twin": "PhysicsCDU",
     "scenario": "warm-water-panic",
     "step": -1,
     "field": "heatRemovedKw",
     "value": 120
    }
   ]
  },
  {
   "id": "M6",
   "title": "Storage arithmetic and the mirrored ack",
   "core": true,
   "idea": {
    "standard": "Every write costs more than one write, and a write the array has acknowledged (acked) already lives in two places.",
    "novice": "Saving one piece of data makes the disks do several jobs. And when the storage answers \"saved\" (the acknowledgement, or ack), the data is already kept in two places in case one fails."
   },
   "prereqs": [],
   "background": {
    "standard": "A drive can fail, so arrays keep redundancy. RAID 10 keeps two full copies of everything, so a write goes to both. RAID 5 and RAID 6 keep one copy plus one or two blocks of parity, check data from which a lost drive can be recomputed. Parity cannot be derived from the new data alone, so a write that touches only part of a stripe is a read-modify-write: read the old data and the old parity, then write the new data and the new parity back.",
    "novice": "A disk can fail, so storage keeps extra information to rebuild from. RAID 10 keeps two full copies of everything, so one save writes twice. RAID 6 keeps one copy plus two pieces of check data (parity). To work out the new check data it first has to read back the old data and the old check data, then write the new data and both new pieces. RAID 5 is the same with one piece instead of two."
   },
   "objectives": [
    {
     "standard": "Compute the RAID write penalty: the backend disk I/Os one host write costs.",
     "novice": "Work out how many disk jobs one save costs."
    },
    {
     "standard": "Explain why the write acknowledgement comes from the NVRAM write cache, not from the capacity SSDs.",
     "novice": "Say why the array can answer \"saved\" before the data reaches the main drives."
    },
    {
     "standard": "Say what two controller nodes share while they boot, and what they share once they serve I/O.",
     "novice": "Say what the two halves of the array share while they start up, and what they share once they are working."
    }
   ],
   "entries": [
    {
     "twin": "PhysicsME5",
     "port": 5214,
     "pageTitle": "PowerVault ME5 RAID Physics Simulator",
     "name": "PowerVault ME5 RAID physics",
     "links": [
      {
       "kind": "scenario",
       "id": "write-penalty",
       "title": "RAID write penalty",
       "label": "RAID write penalty",
       "how": {
        "standard": "The run is a saturating 8 KB pure-write load on RAID 10. Turn on Explain mode in the header first: the served IOPS read differently under the two layouts, but the backend disk I/O does not, and only the Explain card shows why — it spells the ledger out as 4.08k disk = 0.00k × 1 + 2.04k × 2. Note the read / write served IOPS, then change RAID level to RAID 6 in the Build panel and compare both numbers.",
        "novice": "The disks are as busy as they can be, doing only small saves, protected the RAID 10 way. Turn on Explain mode in the strip at the top first — without it the disks look equally busy either way, which is true and is not the point. With it on, the panel shows the sum behind the number. Note the write number, then change RAID level to RAID 6 in the Build panel and read it again."
       }
      },
      {
       "kind": "scenario",
       "id": "second-failure",
       "title": "Second failure, mid-rebuild",
       "label": "Second failure, mid-rebuild",
       "how": {
        "standard": "RAID 6 on 20 TB drives: one drive fails, then a second fails inside the rebuild window. Change RAID level to RAID 5 and run it again.",
        "novice": "One disk fails, then a second one fails while the first is still being rebuilt. Watch whether the data survives, then change RAID level to RAID 5 and run it again."
       }
      },
      {
       "kind": "scenario",
       "id": "controller-failover",
       "title": "Lose a controller",
       "label": "Lose a controller",
       "how": {
        "standard": "On the ME5 the write cache lives inside each controller, mirrored to its partner. Kill one and the cache has no mirror, so the survivor falls back to write-through. Watch the enclosure map: the survivor's cache turns to write-through, the dead controller's cache reads failed, and the banner goes to DEGRADED. Latency moves very little, 29.69 to 30.19 ms — read that as a modelling decision, not as the real price of losing write-back. PhysicsME5 charges a flat failover cost and says in its own footnote that it does not model caching beyond that; a real array losing write-back coalescing at this utilization would pay more. The failure stop below asks the same question of PowerStore.",
        "novice": "This small array keeps its fast save area inside each controller, copied to the other one. When one controller dies there is no second copy, so the survivor stops using the fast area and waits for the disks on every save (write-through). Watch the map: the surviving controller's cache is labelled write-through, the dead one's is labelled failed, and the header says DEGRADED. The waiting time per save barely moves, 29.69 to 30.19 ms. That is because this model charges one flat extra cost rather than working out what losing the fast area really does; the model says so itself in its footnote. Remember this for the question at the end."
       }
      }
     ],
     "note": {
      "standard": "First, the cost of a write on plain disks, with nothing else in the way.",
      "novice": "First: what one save costs on plain disks."
     }
    },
    {
     "twin": "DellPowerStore",
     "port": 5175,
     "pageTitle": "PowerStore Inside",
     "trace": "poweron",
     "name": "PowerStore power-on",
     "links": [
      {
       "kind": "tour",
       "id": "mirrored-ack",
       "label": "Guided tour, at the mirrored acknowledgement"
      },
      {
       "kind": "step",
       "value": 7,
       "expectPhase": "drives",
       "label": "Power-on trace, as the NVRAM write cache initializes",
       "how": {
        "standard": "The link counts steps from zero, so it lands on what the twin's Telemetry panel calls step 8 / 14. The answers below use the screen's numbering.",
        "novice": "The model counts its steps from one, and the answers below use the numbers on its screen."
       }
      },
      {
       "kind": "step",
       "value": 5,
       "expectPhase": "boot",
       "label": "Power-on trace, at the PowerStoreOS boot",
       "how": {
        "standard": "Screen step 6 / 14, the one the third check asks about. Compare its elapsed clock with the step before it, and watch how long Run dwells here.",
        "novice": "The screen calls this one 6 of 14, and the last question asks about it. Look at the clock on this step and on the one before it, and notice how long Run stays here."
       }
      }
     ],
     "note": {
      "standard": "Then, how a larger array acknowledges a write before paying that cost. PowerStore has no fixed RAID groups (its resiliency engine spreads parity across the drives), so the ME5's penalty arithmetic is not repeated here. What this twin shows is where the write cache physically sits. Read step 8 closely and work out for yourself what follows from it; the failure stop below asks exactly that.",
      "novice": "Then: how a bigger array can say \"saved\" before paying that cost. This one keeps its fast save area on special drives (NVRAM) rather than ordinary memory. The screen's step 8 shows where those drives sit. Work out what that means before the question at the end asks you."
     }
    }
   ],
   "predict": {
    "q": {
     "standard": "Same drives, saturating, 8 KB writes and nothing else. RAID 10 against RAID 6: how far apart are the served write IOPS?",
     "novice": "Two ways of protecting the same disks. The disks are as busy as they can be, doing only small saves (8 KB each). How much faster does the first way (RAID 10) save than the second (RAID 6)?"
    },
    "options": [
     "About the same",
     "About 1.5 times",
     "Exactly 3 times",
     "About 6 times"
    ],
    "answer": 2,
    "reveal": {
     "standard": "Exactly 3×. RAID 10 costs 2 backend I/Os per write (one to each copy). RAID 6 costs 6: read the old data and both parity blocks, then write all three back. On screen the served writes read 2.04k on RAID 10 and 0.68k on RAID 6 (illustrative drives). With reads in the mix the gap narrows, because a read costs one I/O at either level — the twin measures about 2.6× at a 30% read share. The ×6 is the partial-stripe price, which is what small writes pay. A write large enough to fill a whole stripe computes its parity from the new data and skips the reads, so sequential streams cost far less; PhysicsME5 carries one penalty per RAID level and lists stripe geometry among the things it does not model.",
     "novice": "Three times. Each save costs RAID 10 two disk jobs, one for each copy. It costs RAID 6 six: read the old data and both pieces of check data, then write all three back. On the screen the writes read 2.04k against 0.68k. Six is the price of small saves. A save big enough to fill a whole stripe works out its check data from the new data and skips the reading, so long streams cost much less than six — the model keeps one number per RAID level and says so."
    },
    "cite": [
     "PhysicsME5/backend/tests/test_engine.py::test_write_penalty_ratio_r10_vs_r6"
    ]
   },
   "checks": [
    {
     "q": {
      "standard": "A second drive fails mid-rebuild. Which survives, RAID 5 or RAID 6?",
      "novice": "A second disk fails while the first is still being rebuilt. Which survives, RAID 5 or RAID 6?"
     },
     "a": {
      "standard": "RAID 6. It carries two parity blocks, so it can lose a second drive inside the rebuild window. RAID 5 carries one, and the same event loses the data.",
      "novice": "RAID 6. It keeps two pieces of check data, so it can rebuild with two disks missing. RAID 5 keeps one, and the same second failure loses the data."
     },
     "cite": [
      "PhysicsME5/backend/tests/test_engine.py::test_second_failure_mid_rebuild_r6_survives_r5_does_not"
     ]
    },
    {
     "q": {
      "standard": "While PowerStore powers up and boots, what state do the two nodes share?",
      "novice": "While the array powers up and boots, does anything on node A ever light up without the matching part on node B? What do the two halves know about each other at that point?"
     },
     "a": {
      "standard": "No cluster state at all. Each node boots independently, off its own flash and its own copy of the operating system, and in the twin nothing crosses between them until the cluster phase — its step 9 is where the nodes find each other. The twin draws them in step: at every power and boot step, whatever lights on node A lights on node B. That symmetry is a modelling choice the twin tests, and so is the clean separation before step 9; a shipping PowerStore has a midplane and a service path, so the hardware is less isolated than the trace draws it. Once they serve I/O the picture reverses: the two nodes share the dual-ported drive bay, and with it the NVRAM write cache every acknowledged write is committed to. Nothing shared while booting, the cache shared while running — that contrast is what the failure stop below turns on.",
      "novice": "No: PSU A lights with PSU B, Fans A with Fans B, every time. The two halves are identical and start side by side, and in this model nothing passes between them yet. They find each other later, at the step called Nodes find each other. Once they are working the answer changes: they share the drive bay, and with it the fast save area that every confirmed save is written to. Nothing shared while starting, the save area shared while running."
     },
     "cite": [
      "DellPowerStore/backend/tests/test_engine.py::test_dual_node_bring_up_is_symmetric"
     ]
    },
    {
     "q": {
      "standard": "Which PowerStore stage is longest, and how can you tell from the screen?",
      "novice": "Which step of the array's start-up is the longest, and how can you tell from the screen?"
     },
     "a": {
      "standard": "PowerStoreOS loads on both nodes, step 6 of 14 on screen. Its text says it is the longest single stage, the elapsed clock jumps from t+40 s to t+150 s across it, and Run dwells there about four times longer than on a normal step (a cycle cost of 4 in the trace, a relative weight and not seconds).",
      "novice": "PowerStoreOS loads on both nodes, step 6 of 14. The text says so, the clock jumps from 40 seconds to 150 seconds on that one step, and Run lingers there."
     },
     "cite": [
      "DellPowerStore/backend/tests/test_engine.py::test_powerstoreos_boot_is_the_longest_stage"
     ]
    }
   ],
   "pins": [
    {
     "twin": "DellPowerStore",
     "step": 5,
     "field": "cycle_cost",
     "value": 4
    },
    {
     "twin": "DellPowerStore",
     "step": 7,
     "field": "phase",
     "value": "drives"
    },
    {
     "twin": "DellPowerStore",
     "step": 4,
     "field": "elapsed_seconds",
     "value": 40
    },
    {
     "twin": "DellPowerStore",
     "step": 5,
     "field": "elapsed_seconds",
     "value": 150
    }
   ],
   "lab": {
    "twin": "PhysicsME5",
    "port": 5214,
    "id": "pay-the-write-tax",
    "title": "Pay the write tax",
    "difficulty": 1,
    "label": "Open the lab: Pay the write tax",
    "goal": {
     "standard": "A write-heavy load on spinning drives, where the RAID write penalty this module measured sets the price of every save. Serve the write rate without saturating, inside the latency ceiling, keeping a hot spare — and then keep as many usable terabytes as you can.",
     "novice": "Lots of saving, on ordinary spinning disks. Every save costs extra disk work, and how much extra depends on the protection scheme you chose. Handle the saving without the disks falling behind, keep a spare drive ready, and still end up with as much usable space as possible."
    },
    "lever": {
     "standard": "The protection level sets the write penalty and the capacity overhead in opposite directions; drive count and type move the ceiling under both.",
     "novice": "The protection choice is the whole puzzle: the cheap-on-space options cost the most per save, and the fast-on-saves options cost the most space."
    },
    "how": {
     "standard": "Open the Labs tab in the app, pick this lab, read its goal and constraints, and build the scenario with the controls this module already used. Run and grade replays the same pure engine and scores the trace: every constraint is measured from the trace, not taken on trust, so an idle build cannot pass. Thresholds and scores are illustrative.",
     "novice": "In the app, open the tab called Labs and choose this lab. It states a goal and some rules. Set the controls the way you think will work, then press Run and grade. The app checks what actually happened in the run, so you cannot pass by doing nothing. Change one setting at a time and grade again. The pass marks are made up for teaching, not measurements."
    },
    "cite": [
     "PhysicsME5/backend/tests/test_labs.py::test_lab_invariants",
     "PhysicsME5/backend/tests/test_labs.py::test_there_are_three_labs_of_rising_difficulty"
    ]
   },
   "bridge": {
    "text": {
     "standard": "PowerStore puts two controllers in front of the drives, and every byte passes through one of them. The next module is about what happens when you delete that controller.",
     "novice": "This storage has two brains in front of its disks, and all data goes through them. Next: storage designs that get rid of that middle layer."
    },
    "next": "M7"
   },
   "failures": [
    {
     "twin": "DellPowerStore",
     "port": 5175,
     "trace": "poweron",
     "name": "PowerStore: node A dies under load",
     "scenario": "node-loss-failover",
     "at": {
      "kind": "phase",
      "value": "degraded"
     },
     "label": "Node-loss trace, paused with node B serving alone",
     "q": {
      "standard": "On the ME5 you watched a controller die and the survivor fall back to write-through, because its write cache lived in the controllers and lost its mirror. A PowerStore with NVRAM drives (any model from the 1000 to the 9200) is serving I/O from both nodes when node A dies. While node B runs alone, does this array fall back to write-through too? And how many acknowledged writes are lost?",
      "novice": "On the small array, losing a controller forced the survivor to stop using its fast save area and wait for the disks (write-through). This bigger array has two controllers sharing the work, and one dies. Does the survivor have to do the same? And how many saves that it had already confirmed to a server are lost?"
     },
     "options": [
      "Yes, write-through; zero lost",
      "No, writes stay mirrored; zero lost",
      "No, writes stay mirrored; the in-flight cache on node A is lost"
     ],
     "answer": 1,
     "a": {
      "standard": "No, and zero. On these models the write cache is not memory inside a node. It is the four NVRAM drives in the shared, dual-ported front bay, worked as mirrored pairs, and the host is acknowledged only after the write is on both drives of a pair — so node B keeps committing every write to two devices exactly as before. The third option describes a node-DRAM cache, which is not what these models have: there is no in-flight buffer inside node A to lose, because the protected copy never lived there. Each node's battery backup unit (the BBU, a battery that holds the array up just long enough to finish writing) powers one drive of every pair, so vaulting — flushing the cache to non-volatile flash on a power loss — still has power on both halves. What the array loses is headroom and controller redundancy: node B goes from 45% to 90% busy (illustrative), which is why the sizing rule is to keep each node under about half load. I/O dips at the fault and is back to full rate before the degraded phase. The entry PowerStore 500 has no NVRAM drives and caches writes in node DRAM, so this answer does not describe it.",
      "novice": "No, and none. On these models the fast write area is not inside either controller. It is four special drives in the shared drive bay that both controllers can reach, kept in mirrored pairs, and a save is only confirmed once it is on both drives of a pair. So the surviving controller carries on exactly as before. The third answer describes a fast area held in the controller's own memory; these models do not have one, so there is nothing inside the dead controller to lose. What the survivor loses is spare capacity: it goes from about half busy to about 90% busy (illustrative numbers), and a second failure would now be an outage. The smallest model, the PowerStore 500, is built differently and this does not apply to it."
     },
     "cite": [
      "DellPowerStore/backend/tests/test_failover.py::test_writes_stay_mirrored_while_single_node",
      "DellPowerStore/backend/tests/test_failover.py::test_no_acknowledged_write_is_ever_lost",
      "DellPowerStore/backend/tests/test_failover.py::test_the_survivor_pays_in_headroom",
      "DellPowerStore/backend/tests/test_failover.py::test_the_nvram_claim_is_scoped_to_models_that_have_nvram"
     ],
     "pins": [
      {
       "step": 0,
       "field": "nodeBLoadPercent",
       "value": 45
      },
      {
       "step": 4,
       "field": "nodeBLoadPercent",
       "value": 90
      },
      {
       "step": 4,
       "field": "writesMirrored",
       "value": true
      },
      {
       "agg": "max",
       "field": "ackedWritesLost",
       "value": 0
      },
      {
       "step": 4,
       "field": "ioPercent",
       "value": 100
      }
     ]
    }
   ],
   "scenarioPins": [
    {
     "twin": "PhysicsME5",
     "scenario": "write-penalty",
     "step": -1,
     "field": "servedWriteKiops",
     "value": 2.04,
     "tol": 0.005
    },
    {
     "twin": "PhysicsME5",
     "scenario": "write-penalty",
     "step": -1,
     "field": "servedWriteKiops",
     "value": 0.68,
     "tol": 0.005,
     "patch": {
      "config": {
       "raidLevel": "6"
      }
     }
    }
   ]
  },
  {
   "id": "M7",
   "title": "Deleting the controller",
   "core": true,
   "idea": {
    "standard": "Scale-out storage removes one thing — the controller in every byte's path, the volume, or the metadata lookup on every read — and the whole design follows from what it removed.",
    "novice": "Big storage systems get simpler by removing one piece: the middleman, the fixed-size box, or the lookup on every read. Each design follows from what it removed."
   },
   "prereqs": [
    "M6"
   ],
   "background": {
    "standard": "A classic array puts a controller in the path of every byte and cuts its capacity into volumes, the fixed containers a host mounts. When a device dies, the array rebuilds what it held. Each twin in this module deletes one of those three things.",
    "novice": "In an ordinary storage system every piece of data passes through one special computer, the controller, and the space is cut into fixed containers called volumes. When a disk dies, the system has to recreate what was on it: a rebuild. Each system in this module throws one of those three things away."
   },
   "objectives": [
    {
     "standard": "Explain why a rebuild gets faster as a scale-out pool grows, and where that stops being true.",
     "novice": "Say why a repair gets quicker as the group of servers grows, and why that cannot go on for ever."
    },
    {
     "standard": "Say what having no volumes means for growth.",
     "novice": "Say what it means for growing a system that its space is never cut into fixed containers."
    },
    {
     "standard": "Explain why the metadata server leaves the data path once the layout is granted.",
     "novice": "Say why the server that knows where everything is stops being involved once a read has started."
    }
   ],
   "entries": [
    {
     "twin": "DellPowerFlex",
     "port": 5189,
     "trace": "cluster",
     "pageTitle": "Dell PowerFlex Inside",
     "name": "PowerFlex software-defined storage",
     "links": [
      {
       "kind": "tour",
       "id": "no-controller",
       "label": "Guided tour, at the missing controller"
      },
      {
       "kind": "tour",
       "id": "every-survivor-rebuilds",
       "label": "Guided tour, as every survivor rebuilds"
      },
      {
       "kind": "phase",
       "value": "rebuild",
       "label": "Cluster trace, at the rebuild",
       "how": {
        "standard": "The link lands on the rebuild step. Read rebuild participants against nodes online, then press Step twice and watch client I/O through protection restored and steady state.",
        "novice": "The link opens at the repair. Compare how many servers are repairing with how many are still running, then press Step twice and watch the client speed number."
       }
      }
     ],
     "note": {
      "standard": "First, the controller deleted: shared block storage assembled out of ordinary servers' local drives.",
      "novice": "First, the middleman removed: shared storage built out of ordinary servers and the disks already inside them."
     }
    },
    {
     "twin": "DellPowerScale",
     "port": 5196,
     "trace": "namespace",
     "pageTitle": "Dell PowerScale Inside",
     "name": "PowerScale scale-out NAS",
     "links": [
      {
       "kind": "tour",
       "id": "add-a-node",
       "label": "Guided tour, as a node is added"
      },
      {
       "kind": "phase",
       "value": "addnode",
       "label": "Namespace trace, at add node",
       "how": {
        "standard": "Read capacity, used percent and migrations required on this one step, then step on through the rebalance and watch which of the three moves.",
        "novice": "On this one step, read how much space there is, how full it is, and how much data an administrator has to move. Then keep stepping and see which of the three changes."
       }
      }
     ],
     "note": {
      "standard": "Then the volume deleted: one file system over every node, so growth is adding a node rather than planning a migration.",
      "novice": "Then the fixed containers removed: one big pool of files spread over every server, so growing it means adding a server rather than planning a move."
     }
    },
    {
     "twin": "DellExascale",
     "port": 5184,
     "trace": "datapath",
     "pageTitle": "Exascale + Lightning Inside",
     "name": "Exascale parallel storage",
     "links": [
      {
       "kind": "tour",
       "id": "metadata-leaves",
       "label": "Guided tour, as metadata leaves the path"
      },
      {
       "kind": "phase",
       "value": "layout",
       "label": "Data-path trace, at the layout",
       "how": {
        "standard": "The metadata server is lit here, and this is the last step at which it is. Note which blocks are dark, then open the next link.",
        "novice": "The server that keeps track of where the pieces are is working here, and this is the last moment it does. Note which blocks are dark, then open the next link."
       }
      },
      {
       "kind": "phase",
       "value": "feed",
       "label": "Data-path trace, at full feed",
       "how": {
        "standard": "All four drawn data servers stream at once and the metadata row reads \"no — bypassed\". The gauge is in terabits; the step text converts it.",
        "novice": "All four storage servers are feeding at the same time, and the row for the map server says it is no longer involved. The gauge counts in terabits and the text underneath turns that into terabytes."
       }
      }
     ],
     "note": {
      "standard": "Last, the lookup deleted from the bulk path — not from the design. A client asks the metadata server once, at open, takes a layout, and reads its stripes straight from every data server named in it. The file system underneath is the scale-out NAS you just saw.",
      "novice": "Last, the lookup on every read removed. A computer asks one server a single question — where are the pieces of this file? — and then reads from all the storage servers at the same time, without asking again. The storage underneath is the same kind you just looked at."
     }
    },
    {
     "twin": "PhysicsStorage",
     "port": 5206,
     "pageTitle": "Storage Platforms &middot; Capacity &amp; Performance Simulator",
     "name": "Storage physics",
     "links": [
      {
       "kind": "scenario",
       "id": "scale-out-rebuild",
       "title": "Scale-up vs scale-out rebuild",
       "label": "Scale-up vs scale-out rebuild",
       "how": {
        "standard": "The preset is a 20-node PowerScale and the scenario fails a drive for you at hour 6 — do not add another. The rebuild finishes inside one hourly tick, so read its length from the log line \"Rebuild complete after 0.45 h (27 min)\" or from the rebuild row under Instruments, which keeps the last rebuild's figure. Then load the PowerStore ×2 preset in the Build panel and read the same line again, and set Nodes to 5 on the PowerScale preset for the third figure.",
        "novice": "The model starts with twenty servers and breaks a disk for you at hour 6, so do not break another. One step of this model is a whole hour and this repair takes less than that, so read its length from the event-log line \"Rebuild complete after 0.45 h (27 min)\", or from the rebuild row under Instruments. Then choose the PowerStore preset in the Build panel and read the same line again. Setting the number of servers to 5 gives the third figure the questions use."
       }
      }
     ],
     "note": {
      "standard": "Finally the same event priced on both architectures, with the rate written down: survivors × per-node contribution against one controller pair's fixed budget.",
      "novice": "Finally, the same broken disk on both kinds of system, with the speed of the repair written down."
     }
    }
   ],
   "predict": {
    "q": {
     "standard": "One of six PowerFlex nodes dies. How many nodes do the rebuild work: one, two, or all five survivors?",
     "novice": "A storage pool is spread over six servers and one of them breaks. How many of the remaining servers help rebuild the lost copies?"
    },
    "options": [
     {
      "standard": "One spare node",
      "novice": "One spare server"
     },
     {
      "standard": "Two partner nodes",
      "novice": "Two partner servers"
     },
     {
      "standard": "All five survivors",
      "novice": "All five remaining servers"
     }
    ],
    "answer": 2,
    "reveal": {
     "standard": "All five survivors. At the rebuild step the number of rebuild participants equals the number of nodes online. A controller array can spread a rebuild over many drives, but all of it runs through one controller pair whose budget is fixed however large the array grows — which is why a bigger pool here rebuilds faster and a bigger array does not.",
     "novice": "All five. Every server that is left helps, at the same time, so the bigger the pool the faster the repair. An ordinary array has one pair of controllers doing that work however big it gets."
    },
    "cite": [
     "DellPowerFlex/backend/tests/test_engine.py::test_every_surviving_node_rebuilds"
    ]
   },
   "checks": [
    {
     "q": {
      "standard": "Does PowerFlex I/O stop during the failure?",
      "novice": "When one of the six servers dies, do the clients stop being served?"
     },
     "a": {
      "standard": "It dips; it does not pause. Client I/O reads 1,800k with six nodes, 1,500k the moment node 6 dies (five nodes at roughly 300k each), 1,380k during the rebuild while repair traffic takes its share, and 1,500k once protection is restored — five nodes' worth, not six. There is no failover gap, but the twin is careful about what its steps are too coarse to draw: requests already in flight to the dead node wait out a timeout of a few seconds before they are retried against the other copy.",
      "novice": "The speed drops; the clients are never left waiting for a changeover. The client number reads 1,800k with six servers, 1,500k as soon as one dies (five servers at about 300 thousand each), 1,380k while the repair runs, and 1,500k afterwards — five servers' worth. Requests that were already on their way to the dead server do wait a few seconds before they are sent to the other copy."
     },
     "cite": [
      "DellPowerFlex/backend/tests/test_engine.py::test_service_survives_the_failure"
     ]
    },
    {
     "q": {
      "standard": "PowerScale grows from 4 to 6 nodes at addnode. What happens to migrations required and to used percent?",
      "novice": "The system grows from 4 servers to 6. What happens to the amount of data an administrator has to move, and to how full the system is?"
     },
     "a": {
      "standard": "Migrations required counts the administrator-planned moves of data across a volume boundary that growth would force; there are no volume boundaries here, so it stays at 0. Capacity goes from 400 to 600 TB and used falls from 81% to 54% — nothing was deleted, and the rebalance that follows spreads data onto the new nodes as a background task, not as a project.",
      "novice": "The amount an administrator has to move stays at zero: there are no fixed containers to move data between. Space goes from 400 to 600 TB and the system goes from 81% full to 54% full, without anything being deleted. The system does shuffle data onto the new servers afterwards, but it does that by itself, in the background, while still serving."
     },
     "cite": [
      "DellPowerScale/backend/tests/test_engine.py::test_growing_the_cluster_requires_no_migration",
      "DellPowerScale/backend/tests/test_engine.py::test_capacity_grows_with_nodes_not_with_planning"
     ]
    },
    {
     "q": {
      "standard": "In which Exascale phases is the metadata server active?",
      "novice": "At which moments is the server that keeps track of where the pieces are actually working?"
     },
     "a": {
      "standard": "Exactly mount and layout — it is absent from every phase that moves bulk data. Throughput peaks at 48,000 Gb/s (about 6 TB/s) with all four drawn data servers streaming; the map's four stand in for roughly forty 1U units in a real rack, so the fan-out requirement is a property of the drawing and 6 TB/s is the rack's figure.",
      "novice": "Only twice: when the connection is made, and when the map of the pieces is handed over. It does no work at all while data is moving. The speed peaks at 48,000 gigabits a second, which is about 6 terabytes a second, with all four storage servers feeding at once — and those four stand for about forty in a real rack."
     },
     "cite": [
      "DellExascale/backend/tests/test_engine.py::test_metadata_leaves_the_data_path",
      "DellExascale/backend/tests/test_engine.py::test_peak_throughput_reaches_rack_scale"
     ]
    },
    {
     "q": {
      "standard": "In the physics app, does a 20-node cluster rebuild faster than a 5-node cluster, and faster than a dual-controller array?",
      "novice": "In the last model, is the repair quicker with twenty servers than with five, and quicker than on an array with two controllers?"
     },
     "a": {
      "standard": "Faster than both: about 0.45 h (27 min) on 20 nodes, 2.1 h on 5, and 3.6 h on the PowerStore ×2 preset, whose rate is one controller pair's fixed budget at any size. The rate is the per-node contribution times the peers that hold the lost data, so it rises with every node added. Rates are illustrative.",
      "novice": "Quicker than both: about 27 minutes with twenty servers, 2.1 hours with five, and 3.6 hours on the two-controller array, which repairs at the same speed however big it is. Every server added puts another helper on the job. The numbers are made up to show the shape, not measured."
     },
     "cite": [
      "PhysicsStorage/backend/tests/test_engine.py::test_rebuild_faster_with_more_nodes_and_the_inversion"
     ]
    }
   ],
   "pins": [
    {
     "twin": "DellPowerFlex",
     "step": 4,
     "field": "iops_thousands",
     "value": 1800
    },
    {
     "twin": "DellPowerFlex",
     "step": 5,
     "field": "iops_thousands",
     "value": 1500
    },
    {
     "twin": "DellPowerFlex",
     "step": 6,
     "field": "rebuild_participants",
     "value": 5
    },
    {
     "twin": "DellPowerFlex",
     "step": 6,
     "field": "nodes_online",
     "value": 5
    },
    {
     "twin": "DellPowerFlex",
     "step": 6,
     "field": "iops_thousands",
     "value": 1380
    },
    {
     "twin": "DellPowerFlex",
     "step": 7,
     "field": "iops_thousands",
     "value": 1500
    },
    {
     "twin": "DellPowerScale",
     "step": 4,
     "field": "used_percent",
     "value": 81
    },
    {
     "twin": "DellPowerScale",
     "step": 5,
     "field": "used_percent",
     "value": 54
    },
    {
     "twin": "DellPowerScale",
     "step": 5,
     "field": "capacity_tb",
     "value": 600
    },
    {
     "twin": "DellPowerScale",
     "step": 5,
     "field": "migrations_required",
     "value": 0
    },
    {
     "twin": "DellExascale",
     "agg": "max",
     "field": "throughput_gbps",
     "value": 48000
    }
   ],
   "scenarioPins": [
    {
     "twin": "PhysicsStorage",
     "scenario": "scale-out-rebuild",
     "step": -1,
     "field": "lastRebuildH",
     "value": 0.45,
     "tol": 0.05
    },
    {
     "twin": "PhysicsStorage",
     "scenario": "scale-out-rebuild",
     "step": -1,
     "field": "lastRebuildH",
     "value": 2.1,
     "tol": 0.1,
     "patch": {
      "config": {
       "units": 5
      }
     }
    },
    {
     "twin": "PhysicsStorage",
     "scenario": "scale-out-rebuild",
     "step": -1,
     "field": "lastRebuildH",
     "value": 3.6,
     "tol": 0.1,
     "patch": {
      "config": {
       "product": "powerstore",
       "units": 2,
       "drivesPerUnit": 12,
       "protection": "raid6"
      }
     }
    }
   ],
   "lab": {
    "twin": "PhysicsStorage",
    "port": 5206,
    "id": "size-for-the-survivor",
    "title": "Size for the survivor's worst hour",
    "difficulty": 1,
    "label": "Open the lab: Size for the survivor's worst hour",
    "goal": {
     "standard": "A controller dies mid-run and a write burst lands after it. Deliver the IOPS through all of it without utilization ever passing the knee — the queueing knee from this module, met on the day half the front end is gone.",
     "novice": "Half way through the run one controller fails, and later a burst of saving arrives. The array has to keep serving the whole time, and never get so busy that waiting times run away. Size it for that hour, not for a quiet one."
    },
    "lever": {
     "standard": "Size against the survivor's share, not the pair's: the knee is a utilization, so the headroom you need is set by the worst moment, not the average.",
     "novice": "Plan for one controller doing all the work, not two sharing it. Waiting time explodes near full, so leave room for the worst moment."
    },
    "how": {
     "standard": "Open the Labs tab in the app, pick this lab, read its goal and constraints, and build the scenario with the controls this module already used. Run and grade replays the same pure engine and scores the trace: every constraint is measured from the trace, not taken on trust, so an idle build cannot pass. Thresholds and scores are illustrative.",
     "novice": "In the app, open the tab called Labs and choose this lab. It states a goal and some rules. Set the controls the way you think will work, then press Run and grade. The app checks what actually happened in the run, so you cannot pass by doing nothing. Change one setting at a time and grade again. The pass marks are made up for teaching, not measurements."
    },
    "cite": [
     "PhysicsStorage/backend/tests/test_labs.py::test_lab_invariants",
     "PhysicsStorage/backend/tests/test_labs.py::test_there_are_three_labs_of_rising_difficulty"
    ]
   },
   "bridge": {
    "text": {
     "standard": "Exascale's fan-out reads converge on one reader at once: the incast the SN6000's congestion control has to absorb. The next module is that network.",
     "novice": "When many storage servers answer one reader at the same moment, the network gets a traffic jam. Next: networks that never drop data, even in a jam."
    },
    "next": "M8"
   }
  },
  {
   "id": "M8",
   "title": "The fabric: lossless two ways",
   "core": true,
   "idea": {
    "standard": "Ethernet (the SN6000 twin) proves losslessness under stress; InfiniBand (the Quantum-X800 twin) makes loss impossible to express.",
    "novice": "One of these two networks, the ordinary kind called Ethernet, reacts fast to traffic jams so nothing gets lost. The other, called InfiniBand, never sends anything until the receiver says it has room, so nothing can get lost."
   },
   "prereqs": [
    "M4",
    "M7"
   ],
   "background": {
    "standard": "NVLink stops at the chassis or rack wall, so traffic between servers is the fabric's job. Incast is the hard case: many senders converging on one receiver at once, with only a switch buffer to absorb it.",
    "novice": "Inside one server, and inside one of those big racks, short private links join the chips. Past that wall the traffic crosses ordinary network cables, and that network is what this module is about. The hard case is called incast: many machines sending to the same machine at the same moment, with only a small waiting space inside the switch to hold what does not fit."
   },
   "objectives": [
    {
     "standard": "Contrast the two ways a fabric avoids loss: Ethernet reacting in time (ECN marking, PFC pauses, adaptive routing) against InfiniBand refusing to transmit without granted buffer credits.",
     "novice": "Say how each of the two networks avoids throwing data away: one notices a cable filling up and reacts in time, the other never sends anything until the receiver has promised it room."
    },
    {
     "standard": "Read the two counters on the Quantum-X800's SHARP step and say what each one measures.",
     "novice": "Read the two meters on the step where the switches start doing the arithmetic themselves, and say what each one counts."
    },
    {
     "standard": "Recognize a gray failure: what the dashboard reports, and what the job experiences.",
     "novice": "Spot a fault the network's own status lights never show, and say how you would notice it anyway."
    }
   ],
   "entries": [
    {
     "twin": "DellPowerSwitchSN6000",
     "port": 5185,
     "pageTitle": "PowerSwitch SN6000 Inside",
     "trace": "fabric",
     "name": "PowerSwitch SN6000 Ethernet fabric",
     "note": {
      "standard": "This is the reacting half of the title: Ethernet, which drops by default, kept lossless by marking, pausing and rerouting in time.",
      "novice": "This is the network that reacts. It is Ethernet, the ordinary kind of network, taught not to throw anything away."
     },
     "links": [
      {
       "kind": "tour",
       "id": "zero-drops-under-stress",
       "label": "Guided tour, at zero drops under stress",
       "how": {
        "standard": "The counters beside the map are the point. Read four rows in order: dropped packets, busiest link, ECN-marked (busiest link), PFC pauses. The ECN row is a percentage of the packets on that one saturated link, not of the fabric's traffic.",
        "novice": "The rows of numbers beside the picture are the point. Read them in order: dropped packets, busiest link, then marked so senders slow down (ECN), then pauses, one traffic class (PFC). Those last two are how this network reacts: a mark tells a sender to ease off, and a pause stops one kind of traffic for an instant. The marked row counts packets on the one busiest cable, not in the whole network."
       }
      },
      {
       "kind": "phase",
       "value": "congestion",
       "label": "Fabric trace, at congestion",
       "how": {
        "standard": "The link opens paused on the congestion step. Read dropped packets and the busiest link, then press Step once for the reroute and read both again, plus fabric throughput.",
        "novice": "The link opens stopped on the step where the network is busiest. Read the dropped packets row and the busiest cable row. Then press Step once, to the next step, and read them again along with the total traffic."
       }
      }
     ]
    },
    {
     "twin": "DellQuantumX800",
     "port": 5202,
     "pageTitle": "Quantum-X800 InfiniBand Inside",
     "trace": "fabric",
     "name": "Quantum-X800 InfiniBand fabric",
     "note": {
      "standard": "The other half of the title: InfiniBand, where a sender may not transmit until the receiver has granted it buffer credits, so loss is not expressible at the link layer. Same two-tier topology, opposite premise.",
      "novice": "Now the other network. Here a sender is not allowed to send anything until the receiver has promised it a place to put it. That promise is called a credit. Nothing can be lost, because nothing is sent without somewhere to land."
     },
     "links": [
      {
       "kind": "tour",
       "id": "credits-before-bytes",
       "label": "Guided tour, at credits before bytes",
       "how": {
        "standard": "Read the sent-without-credit counter. It is zero here for a different reason than the SN6000's dropped-packets zero: not held down by control loops, but unreachable by construction.",
        "novice": "Read the row called sent without credit. It is zero, like the dropped packets row on the other network, but for a different reason: there, the network works hard to keep it at zero; here, there is no way for it to be anything else."
       }
      },
      {
       "kind": "tour",
       "id": "sharp-counters-cross",
       "label": "Guided tour, as the SHARP counters cross",
       "how": {
        "standard": "Two counters move in opposite directions: fabric traffic and effective all-reduce. Note the busiest link on the step before (64%) — the fabric was not congested, so the rate does not rise because congestion eased.",
        "novice": "Watch two meters move opposite ways: the traffic crossing the network goes down, and the speed of useful work goes up. Look at the busiest cable on the step before this one: it is only about two thirds full, so the network was not jammed. Something other than relief is making the work faster."
       }
      },
      {
       "kind": "phase",
       "value": "burst",
       "label": "Fabric trace, at the incast burst",
       "how": {
        "standard": "Many senders converge on one receiver. Read sent without credit, then sender stall: this is where the credit scheme sends its bill.",
        "novice": "Here many machines send to one machine at once. Read the sent without credit row, then the sender stall row: waiting is what this design costs instead of losing data."
       }
      }
     ]
    },
    {
     "twin": "PhysicsFabric",
     "port": 5207,
     "pageTitle": "Network Fabrics &middot; Flow &amp; Congestion Simulator",
     "name": "Fabric physics",
     "note": {
      "standard": "A live simulator rather than a trace: it models this module's two fabrics and a third switch it does not use, the E3200 campus switch from the electives.",
      "novice": "This one is a live simulator, not a recorded sequence. It can model both networks from this module, and a third, smaller office switch that this module does not use."
     },
     "links": [
      {
       "kind": "scenario",
       "id": "gray-failure",
       "title": "Gray failure",
       "label": "Gray failure",
       "how": {
        "standard": "The app opens as a console. Press Run and watch three readings in Instruments: the status line (ALL GREEN, says the fabric), FCT (64 MB), and affected flows (useful traffic). One link starts losing 0.1% of its packets silently at t=180 s. Compare the fabric-wide number with the affected-flow one before you decide how bad this is.",
        "novice": "This page opens as a wall of instruments; ignore most of it. Press Run and watch three readings in the Instruments panel: the status line that says ALL GREEN, the line called FCT (how long one transfer takes), and the line called affected flows. Part-way through the run, one cable quietly starts losing one packet in a thousand. Notice that the whole-network figure and the figure for the traffic actually crossing that cable are very different numbers."
       }
      }
     ]
    }
   ],
   "predict": {
    "q": {
     "standard": "The SN6000's hottest link reaches 98%. How many packets does the fabric drop?",
     "novice": "The busiest cable in the network is 98% full. How many pieces of data get thrown away?"
    },
    "options": [
     "None",
     "A few, then it recovers",
     "About 2% of traffic"
    ],
    "answer": 0,
    "reveal": {
     "standard": "None, on every step. Adaptive routing then cools the hot link to 71% while total fabric throughput rises from 24 to 31 Tb/s.",
     "novice": "None at all. Then the network moves some traffic onto quieter paths, so the busy cable calms down and total traffic actually goes up."
    },
    "cite": [
     "DellPowerSwitchSN6000/backend/tests/test_engine.py::test_fabric_never_drops_a_packet",
     "DellPowerSwitchSN6000/backend/tests/test_engine.py::test_congestion_actually_happens_and_is_survived",
     "DellPowerSwitchSN6000/backend/tests/test_engine.py::test_adaptive_routing_relieves_without_losing_work"
    ]
   },
   "checks": [
    {
     "q": {
      "standard": "When SHARP turns on in the Quantum-X800 twin, what happens to fabric traffic and to the effective all-reduce rate, and why does the rate rise?",
      "novice": "On the step where the switches start adding up the numbers themselves, what happens to the two meters — the traffic crossing the network, and the speed of useful work — and why does the second one go up?"
     },
     "a": {
      "standard": "Fabric traffic falls from 36 to 22 Tb/s while the effective all-reduce rate rises from 1,600 to 2,900 Gb/s. The rate does not rise because congestion eased: the busiest link was 64% on the step before, so nothing was congested. It rises because the reduction stopped being a ring of steps between GPUs and became a tree inside the switches — each contribution crosses the fabric once and is added on the way, and a sum is smaller than the numbers that made it.",
      "novice": "The traffic crossing the network falls, from 36 to 22 (in trillions of bits a second), while the speed of useful work rises, from 1,600 to 2,900 (in billions of bits a second). It is not that the traffic jam cleared: the busiest cable was only about two thirds full before. It speeds up because the adding up now happens inside the switches as the numbers go past, so each machine's numbers cross the network once instead of being passed all the way around the group — and a total is smaller than the numbers that made it."
     },
     "cite": [
      "DellQuantumX800/backend/tests/test_engine.py::test_sharp_moves_the_math_into_the_fabric"
     ]
    },
    {
     "q": {
      "standard": "What does the incast burst cost InfiniBand, if not drops?",
      "novice": "When many machines send to one machine at once, this network loses nothing. So what does it cost instead?"
     },
     "a": {
      "standard": "Stalls: 1,800 µs per second of waiting, on the burst step only, with the busiest link at 97%. Packets sent without a credit stay at 0 everywhere. The bill arrives as waiting, not as lost work.",
      "novice": "Waiting. On that step the senders spend about 1,800 microseconds of every second held up, and the busiest cable is 97% full. The row counting data sent without permission stays at zero, as it does on every step. Nothing is lost; people wait instead."
     },
     "cite": [
      "DellQuantumX800/backend/tests/test_engine.py::test_the_burst_stalls_senders_instead_of_losing_work",
      "DellQuantumX800/backend/tests/test_engine.py::test_no_packet_is_ever_sent_without_a_credit"
     ]
    },
    {
     "q": {
      "standard": "In the physics app, what does the status panel show after a gray failure, and which of its throughput numbers describes what the job feels?",
      "novice": "In the live simulator, what do the status lights say after one cable quietly starts losing data — and which of the two traffic numbers tells you how bad it is for the work being done?"
     },
     "a": {
      "standard": "All green, with the switch-reported drops at zero, while one 64 MB transfer stretches from 0.68 ms to 1.71 ms. Two throughput numbers disagree: fabric-wide delivery is down about 4%, because the sick link is one leaf's share of eight, while goodput on the flows actually crossing it is down 35%. The fabric-wide average is the misleading one here — a collective finishes when its slowest rank does, so 35% is the figure the job feels.",
      "novice": "Every light stays green and the network still reports zero packets thrown away, while one transfer takes about two and a half times as long (0.68 to 1.71 milliseconds). There are two traffic figures and they disagree. Across the whole network, only about 4% of the traffic is missing, because the bad cable carries one eighth of it. For the traffic that actually crosses that cable, 35% is gone. The second number is the one that matters: the team of processors only moves on when its slowest member has finished."
     },
     "cite": [
      "PhysicsFabric/backend/tests/test_engine.py::test_gray_failure_green_and_wrong"
     ]
    }
   ],
   "pins": [
    {
     "twin": "DellPowerSwitchSN6000",
     "step": 6,
     "field": "peak_link_percent",
     "value": 98
    },
    {
     "twin": "DellPowerSwitchSN6000",
     "step": 7,
     "field": "peak_link_percent",
     "value": 71
    },
    {
     "twin": "DellPowerSwitchSN6000",
     "step": 6,
     "field": "fabric_tbps",
     "value": 24
    },
    {
     "twin": "DellPowerSwitchSN6000",
     "step": 7,
     "field": "fabric_tbps",
     "value": 31
    },
    {
     "twin": "DellPowerSwitchSN6000",
     "agg": "max",
     "field": "dropped_packets",
     "value": 0
    },
    {
     "twin": "DellQuantumX800",
     "step": 6,
     "field": "fabric_tbps",
     "value": 36
    },
    {
     "twin": "DellQuantumX800",
     "step": 7,
     "field": "fabric_tbps",
     "value": 22
    },
    {
     "twin": "DellQuantumX800",
     "step": 6,
     "field": "allreduce_gbps",
     "value": 1600
    },
    {
     "twin": "DellQuantumX800",
     "step": 6,
     "field": "peak_link_percent",
     "value": 64
    },
    {
     "twin": "DellQuantumX800",
     "step": 7,
     "field": "allreduce_gbps",
     "value": 2900
    },
    {
     "twin": "DellQuantumX800",
     "step": 8,
     "field": "stall_micros_per_sec",
     "value": 1800
    },
    {
     "twin": "DellQuantumX800",
     "step": 8,
     "field": "peak_link_percent",
     "value": 97
    }
   ],
   "scenarioPins": [
    {
     "twin": "PhysicsFabric",
     "scenario": "gray-failure",
     "step": 100,
     "field": "fctMs",
     "value": 0.68,
     "tol": 0.01
    },
    {
     "twin": "PhysicsFabric",
     "scenario": "gray-failure",
     "step": -1,
     "field": "fctMs",
     "value": 1.71,
     "tol": 0.01
    },
    {
     "twin": "PhysicsFabric",
     "scenario": "gray-failure",
     "step": -1,
     "field": "statusAllGreen",
     "value": true
    },
    {
     "twin": "PhysicsFabric",
     "scenario": "gray-failure",
     "step": -1,
     "field": "droppedPps",
     "value": 0
    },
    {
     "twin": "PhysicsFabric",
     "scenario": "gray-failure",
     "step": -1,
     "field": "affectedFlowPenaltyPct",
     "value": 35
    },
    {
     "twin": "PhysicsFabric",
     "scenario": "gray-failure",
     "step": -1,
     "field": "goodputPenaltyPct",
     "value": 4.4
    }
   ],
   "lab": {
    "twin": "PhysicsFabric",
    "port": 5207,
    "id": "elephants-on-a-budget",
    "title": "Tame the elephants on a power budget",
    "difficulty": 1,
    "label": "Open the lab: Tame the elephants on a power budget",
    "goal": {
     "standard": "Carry a wall of elephant flows with the worst link off its ceiling, inside a fabric power budget — then push the worst link lower still. ECMP hashes flows, not bytes, so the losslessness this module watched is not the same thing as a balanced fabric.",
     "novice": "A few very large transfers have to cross the network, and the busiest link must not run close to full. You also have a limit on how much electricity the switches and optics may use. Spreading traffic is done by a hash of each flow, so a handful of big flows can land on the same link no matter how much capacity exists."
    },
    "lever": {
     "standard": "More spines buy balance and cost optics power; adaptive routing buys it without the ports. Read both against the budget.",
     "novice": "You can add more switches (which costs power) or turn on routing that moves traffic off a busy link (which does not)."
    },
    "how": {
     "standard": "Open the Labs tab in the app, pick this lab, read its goal and constraints, and build the scenario with the controls this module already used. Run and grade replays the same pure engine and scores the trace: every constraint is measured from the trace, not taken on trust, so an idle build cannot pass. Thresholds and scores are illustrative.",
     "novice": "In the app, open the tab called Labs and choose this lab. It states a goal and some rules. Set the controls the way you think will work, then press Run and grade. The app checks what actually happened in the run, so you cannot pass by doing nothing. Change one setting at a time and grade again. The pass marks are made up for teaching, not measurements."
    },
    "cite": [
     "PhysicsFabric/backend/tests/test_labs.py::test_lab_invariants",
     "PhysicsFabric/backend/tests/test_labs.py::test_there_are_three_labs_of_rising_difficulty"
    ]
   },
   "bridge": {
    "text": {
     "standard": "A gray failure is damage the dashboard does not show. Ransomware has the same shape, so the next module starts from the question the gray link raises: what can you still trust?",
     "novice": "Some problems don't show up on the dashboard at all. Ransomware is like that. Next: how to keep a safe copy, prove it is clean, and keep attackers away from it."
    },
    "next": "M9"
   },
   "failures": [
    {
     "twin": "DellPowerSwitchSN6000",
     "port": 5185,
     "trace": "fabric",
     "name": "SN6000: the gray link that reads green",
     "scenario": "gray-link",
     "at": {
      "kind": "phase",
      "value": "blind"
     },
     "label": "Gray-link trace, paused while every link still reports up",
     "q": {
      "standard": "One leaf-to-spine optic starts corrupting frames and the all-reduce stretches from 120 ms to 205 ms. What does the link-state panel show during the slowdown, what does the dropped-packets counter read, and at which step does job throughput come back: when telemetry names the bad link, or later?",
      "novice": "One cable end in the network starts garbling data and the training job slows down by more than half. What do the network's status lights show? How many packets does the network say it dropped? And does the job speed up again as soon as someone finds the bad link?"
     },
     "options": [
      "One link down, drops climbing, recovery when telemetry finds it",
      "All links up, zero drops, recovery when telemetry finds it",
      "All links up, zero drops, recovery only when an operator steers traffic off the link"
     ],
     "answer": 2,
     "a": {
      "standard": "All 8 uplinks read up the whole time: the link errs below the threshold at which its own physical layer would take it down. droppedPackets stays 0, because no buffer overflowed; the loss is corruption, counted as NIC retransmits. Naming the link fixes nothing: throughput on the telemetry step equals the blind steps, 17 Tb/s. It recovers only at the steer step, when an operator withdraws routing from the link so it leaves the equal-cost group while still up (26 Tb/s, 134 ms, the surviving leaf-2 uplink at 92%), and returns to the healthy 29 Tb/s only after the port is shut, the optic replaced and the link retrained. Adaptive routing does not help unprompted: it picks paths by queue occupancy and utilization, and a corrupting link is not congested. NVIDIA's published account of this fault disables the port directly; withdrawing routing first is operator practice. Figures are illustrative.",
      "novice": "Every link shows as working, and the dropped-packet count stays at zero. Nothing overflowed; the data is being damaged in flight and quietly sent again, which is what makes the job slow. Finding the bad link does not fix anything by itself. The job speeds up only when a person tells the network to stop using that link, and gets back to full speed only after the faulty part is replaced. The network's automatic path-picking does not help, because it avoids busy links, and a link that garbles data is not busy. The numbers are illustrative."
     },
     "cite": [
      "DellPowerSwitchSN6000/backend/tests/test_gray_link.py::test_throughput_recovers_only_after_traffic_is_steered",
      "DellPowerSwitchSN6000/backend/tests/test_gray_link.py::test_the_sick_link_reports_up_through_the_blind_steps",
      "DellPowerSwitchSN6000/backend/tests/test_gray_link.py::test_finding_the_link_fixes_nothing",
      "DellPowerSwitchSN6000/backend/tests/test_gray_link.py::test_congestion_loss_is_still_zero",
      "DellPowerSwitchSN6000/backend/tests/test_gray_link.py::test_moving_traffic_is_an_operator_action_not_adaptive_routing"
     ],
     "pins": [
      {
       "step": 0,
       "field": "collectiveMs",
       "value": 120
      },
      {
       "step": 2,
       "field": "collectiveMs",
       "value": 205
      },
      {
       "step": 2,
       "field": "sickLinkStatus",
       "value": "up"
      },
      {
       "step": 4,
       "field": "fabricTbps",
       "value": 17
      },
      {
       "step": 5,
       "field": "fabricTbps",
       "value": 26
      },
      {
       "step": 5,
       "field": "collectiveMs",
       "value": 134
      },
      {
       "step": 5,
       "field": "peakLinkPercent",
       "value": 92
      },
      {
       "step": 8,
       "field": "fabricTbps",
       "value": 29
      },
      {
       "agg": "max",
       "field": "droppedPackets",
       "value": 0
      }
     ]
    }
   ]
  },
  {
   "id": "M9",
   "title": "Survive, verify, contain",
   "core": true,
   "idea": {
    "standard": "Three separate questions: does a copy survive, is it clean, and who can reach it.",
    "novice": "Protecting data is three different jobs that people often mix up: keeping a copy that attackers can't touch, checking that copy isn't already damaged, and controlling who can get in at all."
   },
   "prereqs": [
    "M6"
   ],
   "background": {
    "standard": "Snapshots and deduplication.",
    "novice": "A snapshot is a saved picture of the data exactly as it was at one moment. Deduplication means storing each repeated piece of data once, so many backups take far less room than their sizes added up."
   },
   "objectives": [
    {
     "standard": "Tell apart isolation (does a copy survive), integrity (is the copy clean) and access (who can reach the data).",
     "novice": "Keep three jobs apart, because they are usually run together and solve different problems: keeping a copy an attacker cannot reach, checking that copy is not already damaged, and controlling who can get to the data at all."
    },
    {
     "standard": "Explain why recovery time is set by the decision plus the bandwidth.",
     "novice": "Explain why getting the systems back takes as long as it does: the hours people spend deciding which copy to use and checking it, plus the hours the data spends travelling down the wire."
    }
   ],
   "entries": [
    {
     "twin": "DellPowerProtect",
     "port": 5183,
     "trace": "lifecycle",
     "name": "PowerProtect and the cyber vault",
     "links": [
      {
       "kind": "tour",
       "id": "airgap-discipline",
       "label": "Guided tour, at air-gap discipline"
      },
      {
       "kind": "phase",
       "value": "attack",
       "label": "Lifecycle trace, at the attack",
       "how": {
        "standard": "Watch the air gap row in Telemetry and the right-hand half of the map. At the attack the gap reads closed and every vault block is dark, and the attack never had a route to try.",
        "novice": "Look at the row called air gap and at the right-hand side of the picture. During the attack the gap says closed and everything on the vault side stays dark. Nothing stopped the attack there; there was simply no way through."
       }
      }
     ],
     "pageTitle": "PowerProtect Inside",
     "note": {
      "standard": "First question: does a copy survive at all. The vault's power is that nothing in production can reach it, not that its hardware is better.",
      "novice": "First question: is there still a good copy anywhere. What protects the locked-away copy is that nothing in the attacked network can get to it."
     }
    },
    {
     "twin": "DellCyberDetect",
     "port": 5192,
     "trace": "detect",
     "name": "Cyber Detect",
     "links": [
      {
       "kind": "tour",
       "id": "blind-then-read",
       "label": "Guided tour, blind then reading",
       "lockedLabel": "Guided tour, the detection story"
      },
      {
       "kind": "phase",
       "value": "blind",
       "label": "Detection trace, while metadata is blind",
       "lockedLabel": "Detection trace, part-way through the attack",
       "how": {
        "standard": "Read the snapshots corrupted row against the metadata alerts row, then look at the timeline: every snapshot is drawn identically, because at that moment they genuinely cannot be told apart.",
        "novice": "Read the row counting damaged copies against the row counting alarms. Then look at the row of copies: they all look the same, because at that moment they really are impossible to tell apart. That is where the administrator is standing."
       }
      },
      {
       "kind": "phase",
       "value": "verdict",
       "label": "Detection trace, at the verdict",
       "how": {
        "standard": "The deliverable is a date, not an alert: the last clean copy row names snapshot 3, and content confidence has moved from a dash to 99%.",
        "novice": "What the analysis hands back is a date, not an alarm: the last good copy row now names a copy, and the confidence row has gone from a dash to 99%."
       }
      }
     ],
     "pageTitle": "Dell Cyber Detect Inside",
     "note": {
      "standard": "Second question, and a different one: the copy survived, but is it already corrupted. Cyber Detect reads the bytes inside each snapshot instead of the descriptions around them.",
      "novice": "Second question, and it is not the same one: the copy survived, but was it already damaged before it was saved? This model opens the copies and reads what is inside them, instead of looking at their names and dates."
     }
    },
    {
     "twin": "DellFortZero",
     "port": 5195,
     "trace": "access",
     "name": "Fort Zero zero trust",
     "links": [
      {
       "kind": "tour",
       "id": "breach-reaches-nothing",
       "label": "Guided tour, where the breach reaches nothing"
      },
      {
       "kind": "phase",
       "value": "grant",
       "label": "Access trace, at an approved request and its lease",
       "how": {
        "standard": "An approved request reaches one resource, and the grant remaining row starts at 300s. Access is a lease with an end, not a property someone now has.",
        "novice": "A request that was approved reaches exactly one thing, and the row grant remaining starts at 300s, five minutes, counting down. Permission here has an end built into it."
       }
      },
      {
       "kind": "phase",
       "value": "breach",
       "label": "Access trace, at the breach",
       "how": {
        "standard": "The attacker is genuinely inside the network here. Read resources reachable and implicit trust grants: both 0, and grant remaining is a dash, because outside a grant there is no lease at all.",
        "novice": "Here the attacker really is inside the office network. Read the two rows: things it can reach, 0, and access given just for being inside, 0. The grant remaining row is a dash, because there is no permission running."
       }
      }
     ],
     "pageTitle": "Dell Project Fort Zero Inside",
     "note": {
      "standard": "Third question, separate again: who can reach the data at all. Isolation and integrity both assume an attacker already inside; this is what being inside buys.",
      "novice": "Third question, and again a different one: who can get to the data in the first place. The two models above both assume an attacker is already inside the network. This one asks what being inside is actually worth."
     }
    },
    {
     "twin": "PhysicsResilience",
     "port": 5209,
     "name": "Resilience physics",
     "links": [
      {
       "kind": "scenario",
       "id": "backups-arent-enough",
       "title": "Backups aren't enough",
       "label": "Backups aren't enough",
       "how": {
        "standard": "Corruption starts at hour 240 and takes the backup repository with it, because production can reach it. Watch copies intact, repo then vault: 9 and 9 before, 0 and 9 when the restore is ordered at hour 290. Copies accrue one a day, so ten exist by hour 240 and the vault holds nine; the tenth was taken in the hour the corruption started. Then press Repository only under Architecture and play it again: the log at hour 290 reads no backup exists intact.",
        "novice": "At hour 240 the damage starts and the ordinary backup store goes with it, because the attacked systems can reach it. Watch the row counting copies still good on each side of the gap: nine and nine before, then 0 for the repository and 9 for the vault when the restore is ordered at hour 290. Copies build up one a day, so ten exist by hour 240 and nine made it into the vault. Then press Repository only on the left and play it again: with no vault, the log says no backup exists intact."
       }
      },
      {
       "kind": "scenario",
       "id": "rto-surprise",
       "title": "The RTO surprise",
       "label": "The RTO surprise",
       "how": {
        "standard": "Instruments shows the two terms of the recovery time separately: about 6 h deciding and validating, and about 55.6 h moving 200 TB at 1 GB/s, so about 62 h from the restore order. Then drag Restore pipe to 4 GB/s and rerun: the transfer term divides, the decision term does not.",
        "novice": "The screen splits the recovery time into its two parts: about 6 hours deciding and checking, and about 56 hours moving 200 TB down a 1 GB per second pipe, about 62 hours in all. Then drag the slider called Restore pipe to 4 GB/s and play it again: the moving part shrinks, the deciding part does not."
       }
      }
     ],
     "pageTitle": "Security &amp; Resilience &middot; Timeline Simulator",
     "note": {
      "standard": "Now the three questions together on one clock, with the hours priced. This app opens as a dense console and starts playing on its own: the button reads Pause because the run is already going.",
      "novice": "Now all three questions at once, on one clock, with the hours counted. This page is busy, and it starts playing by itself: the button says Pause because the run is already under way, not because it is stuck."
     }
    }
   ],
   "predict": {
    "q": {
     "standard": "Ransomware encrypts snapshots over several days. How many alerts does metadata-based detection raise before byte-level inspection runs?",
     "novice": "Ransomware quietly scrambles saved copies over several days. A monitor watches file names, how many files change at once, and how busy the disks are. How many alarms does it raise?"
    },
    "options": [
     "Zero",
     "One, on the first encrypted snapshot",
     "One per encrypted snapshot"
    ],
    "answer": 0,
    "reveal": {
     "standard": "Zero. At the blind step 4 of 7 snapshots are corrupted and metadata alerts are still 0. Content confidence reads nothing at all, a dash, because nothing has read the bytes yet; once inspection runs it reads 99%, and the verdict names snapshot 3 as the last clean copy.",
     "novice": "None. Four of seven copies are already damaged and the monitor is silent. The confidence row is a dash, not a zero, because nothing has looked inside the copies yet. Only reading the actual bytes finds the damage, and what comes back is not an alarm but a date: the last good copy."
    },
    "cite": [
     "DellCyberDetect/backend/tests/test_engine.py::test_metadata_detection_is_blind_while_corruption_spreads",
     "DellCyberDetect/backend/tests/test_engine.py::test_confidence_comes_only_from_reading_content",
     "DellCyberDetect/backend/tests/test_engine.py::test_the_named_copy_is_actually_clean"
    ]
   },
   "checks": [
    {
     "q": {
      "standard": "In PowerProtect, in which phases is the air gap open?",
      "novice": "In the PowerProtect model, at which moments is the gap between production and the vault open?"
     },
     "a": {
      "standard": "Only replicate and recover. During the attack no vault region and no gap region is active, and the Telemetry row reads air gap: closed.",
      "novice": "Twice, and only twice: when a copy is taken into the vault, and when clean data is sent back out. Both times the vault opens it. During the attack the gap is shut, the whole right-hand half of the map stays dark, and the air gap row reads closed."
     },
     "cite": [
      "DellPowerProtect/backend/tests/test_engine.py::test_air_gap_discipline",
      "DellPowerProtect/backend/tests/test_engine.py::test_attack_cannot_reach_the_vault"
     ]
    },
    {
     "q": {
      "standard": "What dedupe ratio does PowerProtect's trace reach?",
      "novice": "The model says the estate has protected 500 TB, while only 25 TB is really stored. What does that mean, and what is it as a ratio?"
     },
     "a": {
      "standard": "20:1: 500 TB logical stored in 25 TB. The test requires at least 10:1.",
      "novice": "Twenty to one. Repeated pieces of data are kept once, so backups the estate counts as 500 TB take 25 TB of real flash. The model's own test only demands ten to one; this run reaches twenty."
     },
     "cite": [
      "DellPowerProtect/backend/tests/test_engine.py::test_dedupe_economics"
     ]
    },
    {
     "q": {
      "standard": "In Fort Zero the attacker holds an inside position at breach. How many resources can it reach?",
      "novice": "In the Fort Zero model an attacker is already inside the office network, the place a wall-based design calls safe. How many things can it get to?"
     },
     "a": {
      "standard": "None: at the breach step the screen reads resources reachable 0 while inside. Implicit trust grants are 0 on every step, and even a legitimate grant reaches at most one resource on a lease, which the grant step shows as grant remaining 300s.",
      "novice": "Nothing at all. Being inside is worth no access: the row called implicit trust grants reads 0 on every single step, the breach included, and resources reachable reads 0 while inside. Even a genuine, approved request reaches only one thing, and only for a while: open the grant step and the row grant remaining counts down from 300s, five minutes."
     },
     "cite": [
      "DellFortZero/backend/tests/test_engine.py::test_the_breach_reaches_nothing",
      "DellFortZero/backend/tests/test_engine.py::test_the_breach_is_actually_inside",
      "DellFortZero/backend/tests/test_engine.py::test_least_privilege_is_literal"
     ]
    },
    {
     "q": {
      "standard": "In the physics app, why does a 200 TB restore at 1 GB/s take days even with a clean copy?",
      "novice": "The right copy survived and it is undamaged. Why does getting the systems back still take days?"
     },
     "a": {
      "standard": "Recovery time is the decision time plus terabytes divided by bandwidth: 6 h deciding and validating, plus 200 TB at 1 GB/s, which is about 55.6 h, so about 62 h in all. Instruments shows the two terms as separate rows, and a faster pipe divides only the second. The test pins the total above 48 hours.",
      "novice": "Because two separate things take time and only one of them is the copying. About 6 hours go on choosing a copy and checking it is safe. Then 200 TB has to travel down a pipe that carries 1 GB every second, which is about 56 hours. Together, about 62 hours, more than two days. A wider pipe shortens the second part and leaves the first alone."
     },
     "cite": [
      "PhysicsResilience/backend/tests/test_engine.py::test_rto_is_decision_plus_bandwidth"
     ]
    }
   ],
   "pins": [
    {
     "twin": "DellCyberDetect",
     "step": 3,
     "field": "snapshots_corrupted",
     "value": 4
    },
    {
     "twin": "DellCyberDetect",
     "step": 3,
     "field": "metadata_alerts",
     "value": 0
    },
    {
     "twin": "DellCyberDetect",
     "step": 5,
     "field": "content_confidence_percent",
     "value": 99
    },
    {
     "twin": "DellCyberDetect",
     "step": 6,
     "field": "last_clean_snapshot",
     "value": 3
    },
    {
     "twin": "DellPowerProtect",
     "step": 2,
     "field": "logical_tb",
     "value": 500
    },
    {
     "twin": "DellPowerProtect",
     "step": 2,
     "field": "stored_tb",
     "value": 25
    },
    {
     "twin": "DellFortZero",
     "step": 5,
     "field": "trust_ttl_seconds",
     "value": 300
    },
    {
     "twin": "DellFortZero",
     "step": 8,
     "field": "resources_reachable",
     "value": 0
    }
   ],
   "lab": {
    "twin": "PhysicsResilience",
    "port": 5209,
    "id": "back-within-a-day",
    "title": "Back within a day, losing as little as you can",
    "difficulty": 1,
    "label": "Open the lab: Back within a day, losing as little as you can",
    "goal": {
     "standard": "An incident corrupts part of the estate before anyone contains it. Build the architecture that recovers anyway inside the recovery-time budget, then shrink the age of the newest intact copy. Only a vaulted copy survives — the air gap this module asserted is what makes the lab winnable at all.",
     "novice": "Something destroys part of the data before anyone stops it. Build a setup that gets the business running again within a day, and then make the surviving copy as recent as you can. Copies that the attack can reach do not count."
    },
    "lever": {
     "standard": "Restore time is decision time plus terabytes over the restore pipe; the RPO follows the vault's cadence, not the backup schedule.",
     "novice": "Getting back takes two things: how long people take to decide, and how fast the data can be copied back. How much you lose depends on how often the protected copy is refreshed."
    },
    "how": {
     "standard": "Open the Labs tab in the app, pick this lab, read its goal and constraints, and build the scenario with the controls this module already used. Run and grade replays the same pure engine and scores the trace: every constraint is measured from the trace, not taken on trust, so an idle build cannot pass. Thresholds and scores are illustrative.",
     "novice": "In the app, open the tab called Labs and choose this lab. It states a goal and some rules. Set the controls the way you think will work, then press Run and grade. The app checks what actually happened in the run, so you cannot pass by doing nothing. Change one setting at a time and grade again. The pass marks are made up for teaching, not measurements."
    },
    "cite": [
     "PhysicsResilience/backend/tests/test_labs.py::test_lab_invariants",
     "PhysicsResilience/backend/tests/test_labs.py::test_there_are_three_labs_of_rising_difficulty"
    ]
   },
   "bridge": {
    "text": {
     "standard": "Every one of these depended on someone watching. The next module is the watching, and the rest of the operations bill.",
     "novice": "All of this only works if someone is paying attention. Next: running and watching a whole estate of machines."
    },
    "next": "M10"
   },
   "failures": [
    {
     "twin": "DellPowerProtect",
     "port": 5183,
     "trace": "lifecycle",
     "name": "Data Domain: the clean that returns less than promised",
     "scenario": "cleaning-gc",
     "at": {
      "kind": "step",
      "value": 5,
      "expectPhase": "clean"
     },
     "label": "Cleaning trace, paused as the first clean lands",
     "q": {
      "standard": "The Data Domain is 96% full and reports 21 TB cleanable. Retention has already expired the old backups. When the weekly clean finishes, how much space comes back: 21 TB, more, or less, and why?",
      "novice": "A backup appliance is 96% full. Old backups have already been marked as expired, and the system says 21 TB can be cleaned up. When the weekly clean-up finishes, do you get 21 TB back, more, or less?"
     },
     "options": [
      "21 TB, the estimate is exact",
      "More, because expired locked data goes too",
      "Less, because something still references part of it"
     ],
     "answer": 2,
     "a": {
      "standard": "Less: 12 TB (illustrative). Expiry freed nothing by itself; stored terabytes fall only during a clean, and a clean frees only segments nothing references. The other 9 TB of the estimate belongs to deleted files still referenced by a lagging MTree replication snapshot (6 TB) and a forgotten snapshot (3 TB). Letting replication catch up and expiring the snapshot releases those 9 TB for a second clean, and the two cleans together return the 21 TB first estimated; Dell's KB says cleaning may need several runs. A further 3 TB the backup catalog calls expired was never in the estimate: it is under Retention Lock, the delete was refused, and it stays until its date.",
      "novice": "Less: 12 TB in this model. Marking a backup as expired does not free any space; only the clean-up does, and it can only remove data that nothing else still points to. The missing 9 TB is still pointed to by a copy job that has fallen behind (6 TB) and an old snapshot someone forgot (3 TB). Fix those two, run the clean-up again, and the rest comes back. Another 3 TB is locked against deletion until a set date, and no clean-up will touch it before then. The numbers are illustrative."
     },
     "cite": [
      "DellPowerProtect/backend/tests/test_cleaning_scenario.py::test_the_first_clean_returns_less_than_the_estimate",
      "DellPowerProtect/backend/tests/test_cleaning_scenario.py::test_expiry_alone_never_frees_space",
      "DellPowerProtect/backend/tests/test_cleaning_scenario.py::test_locked_files_are_never_counted_as_cleanable",
      "DellPowerProtect/backend/tests/test_cleaning_scenario.py::test_locked_data_is_never_reclaimed_before_its_lock_ends"
     ],
     "pins": [
      {
       "step": 3,
       "field": "storedTb",
       "value": 96
      },
      {
       "step": 3,
       "field": "cleanableTb",
       "value": 21
      },
      {
       "step": 5,
       "field": "reclaimedTb",
       "value": 12
      },
      {
       "step": 5,
       "field": "heldByReplicationTb",
       "value": 6
      },
      {
       "step": 5,
       "field": "heldBySnapshotTb",
       "value": 3
      },
      {
       "step": 5,
       "field": "heldByLockTb",
       "value": 3
      },
      {
       "step": 8,
       "field": "reclaimedTb",
       "value": 21
      }
     ]
    },
    {
     "twin": "DellCyberDetect",
     "port": 5192,
     "trace": "detect",
     "name": "Cyber Detect: the attacker outwaits the snapshots",
     "scenario": "dwell-exceeds-retention",
     "at": {
      "kind": "phase",
      "value": "verdict"
     },
     "label": "Dwell-exceeds-retention trace, paused at the verdict",
     "q": {
      "standard": "The attacker has corrupted data slowly for longer than the array's seven-day snapshot retention, so all seven retained snapshots are corrupted when content inspection runs. The administrator needs a restore point now. Which snapshot does Cyber Detect name as the last clean copy, and where does the recovery come from?",
      "novice": "An attacker has been quietly damaging data for more than a week, and the array only keeps a week of snapshots. So every snapshot it still has is damaged. Someone needs to restore right now. Which snapshot does the product say is safe?"
     },
     "options": [
      "The oldest snapshot, as the least damaged",
      "The newest snapshot, as the most complete",
      "None; recovery has to come from off the array"
     ],
     "answer": 2,
     "a": {
      "standard": "None. lastCleanSnapshot stays at -1 for the whole trace and the verdict reads no clean copy on this array. Naming the least-bad snapshot would be a false negative with a certificate on it, the one error the product exists to prevent. Recovery comes from the isolated PowerProtect Cyber Recovery vault, which holds replicated backup copies, not array snapshots, and recovers through a host inside the vault. That works only because the scenario assumes the volume was in the backup set and the vault keeps copies longer than the attacker waited. The data is saved, but the restored copy is strictly older, about 310 h against the baseline's 134 h. Hours and retention windows are illustrative, and the every-copy-suspicious sequence is this twin's reading, not a documented Dell walkthrough.",
      "novice": "None of them. The product refuses to call a damaged copy safe, even the least damaged one, because a wrong all-clear is the worst mistake it could make. The restore has to come from somewhere else: the separate, locked-away backup vault. That only works if this data was being backed up there and the vault keeps copies for longer than the attacker waited. The data is saved, but from an older point in time, so more recent work is lost. The hours in the model are illustrative."
     },
     "cite": [
      "DellCyberDetect/backend/tests/test_scenarios.py::test_a_corrupted_copy_is_never_certified_clean",
      "DellCyberDetect/backend/tests/test_scenarios.py::test_recovery_names_an_off_array_source",
      "DellCyberDetect/backend/tests/test_scenarios.py::test_the_price_is_the_recovery_point"
     ],
     "pins": [
      {
       "step": 6,
       "field": "lastCleanSnapshot",
       "value": -1
      },
      {
       "step": 6,
       "field": "snapshotsCorrupted",
       "value": 7
      },
      {
       "step": 6,
       "field": "verdict",
       "value": "no-clean-copy-on-array"
      },
      {
       "step": 7,
       "field": "recoverySource",
       "value": "powerprotect-vault"
      },
      {
       "step": 7,
       "field": "recoveryPointAgeHours",
       "value": 310
      }
     ]
    }
   ],
   "scenarioPins": [
    {
     "twin": "PhysicsResilience",
     "scenario": "rto-surprise",
     "step": -1,
     "field": "decisionHours",
     "value": 6
    },
    {
     "twin": "PhysicsResilience",
     "scenario": "rto-surprise",
     "step": -1,
     "field": "transferHours",
     "value": 55.6
    },
    {
     "twin": "PhysicsResilience",
     "scenario": "rto-surprise",
     "step": -1,
     "field": "rtoHours",
     "value": 62
    },
    {
     "twin": "PhysicsResilience",
     "scenario": "backups-arent-enough",
     "step": 239,
     "field": "vaultCopiesIntact",
     "value": 9
    },
    {
     "twin": "PhysicsResilience",
     "scenario": "backups-arent-enough",
     "step": 290,
     "field": "repoCopiesIntact",
     "value": 0
    },
    {
     "twin": "PhysicsResilience",
     "scenario": "backups-arent-enough",
     "step": 290,
     "field": "vaultCopiesIntact",
     "value": 9
    }
   ]
  },
  {
   "id": "M10",
   "title": "Running the estate",
   "core": true,
   "idea": {
    "standard": "Operations is where the architecture choices send their bills.",
    "novice": "How a system is built decides how much work it takes to run it later. This module shows where that work comes from."
   },
   "prereqs": [
    "M2",
    "M7"
   ],
   "background": {
    "standard": "iDRAC's out-of-band management, and clusters.",
    "novice": "The small management computer inside a server, which works whether or not the server itself is on, and the idea of a cluster: several machines run as one."
   },
   "objectives": [
    {
     "standard": "Follow telemetry to an insight.",
     "novice": "Follow a measurement from the equipment to a warning somebody can act on."
    },
    {
     "standard": "Contrast hyperconverged coupling (VxRail) with disaggregated pools (Private Cloud).",
     "novice": "Compare all-in-one servers, which arrive with their storage attached, against storage and computing bought separately."
    },
    {
     "standard": "Explain zero-touch as attestation first.",
     "novice": "Say why a new machine has to prove it is genuine before it is given anything to run."
    },
    {
     "standard": "Price manual against automated operations.",
     "novice": "Work out what doing the work by hand costs in hours against letting software do it."
    }
   ],
   "entries": [
    {
     "twin": "DellCloudIQ",
     "port": 5180,
     "trace": "pipeline",
     "name": "CloudIQ AIOps",
     "links": [
      {
       "kind": "tour",
       "id": "analyze-dip",
       "label": "Guided tour, at the health dip"
      },
      {
       "kind": "phase",
       "value": "detect",
       "label": "Pipeline trace, at detection"
      }
     ],
     "pageTitle": "CloudIQ Inside"
    },
    {
     "twin": "DellVxRail",
     "port": 5179,
     "trace": "firstrun",
     "name": "VxRail first run",
     "links": [
      {
       "kind": "tour",
       "id": "primary-election",
       "label": "Guided tour, at the primary election"
      },
      {
       "kind": "phase",
       "value": "primary",
       "label": "First-run trace, at the election"
      }
     ],
     "pageTitle": "VxRail Inside",
     "note": {
      "standard": "The score CloudIQ watched belongs to an estate somebody chose the shape of. This is the first shape: a cluster whose compute and storage arrive fused in one node and bring up together.",
      "novice": "The health score you just watched comes from equipment somebody chose. Here is the first choice: servers that arrive with their storage built in, so the two always come together."
     }
    },
    {
     "twin": "DellPrivateCloud",
     "port": 5198,
     "trace": "cloud",
     "name": "Dell Private Cloud",
     "links": [
      {
       "kind": "tour",
       "id": "storage-grows-alone",
       "label": "Guided tour, as storage grows alone"
      },
      {
       "kind": "tour",
       "id": "hypervisor-switch",
       "label": "Guided tour, at the hypervisor switch"
      },
      {
       "kind": "phase",
       "value": "growstorage",
       "label": "Cloud trace, as storage grows"
      }
     ],
     "pageTitle": "Dell Private Cloud Inside",
     "note": {
      "standard": "The same estate with the coupling taken out: compute, storage and network bought and grown separately under one control plane. Read it against VxRail rather than on its own, because the argument is about what each shape costs later.",
      "novice": "The same job built the other way: computing, storage and network bought separately and run from one place. Read it next to the page before it, not on its own."
     }
    },
    {
     "twin": "DellNativeEdge",
     "port": 5187,
     "trace": "onboard",
     "name": "NativeEdge zero-touch onboarding",
     "links": [
      {
       "kind": "tour",
       "id": "zero-touch",
       "label": "Guided tour, at zero touch"
      },
      {
       "kind": "phase",
       "value": "attest",
       "label": "Onboarding trace, at attestation"
      }
     ],
     "pageTitle": "NativeEdge Inside",
     "note": {
      "standard": "The same effort question away from the data centre: hundreds of sites with nobody technical on them. Dell renamed NativeEdge to Distributed Private Cloud in May 2026, so the twin's own sources carry both names; this is the edge platform, not the private-cloud stack in the entry above.",
      "novice": "The same question, now far from the data centre: hundreds of small sites with no IT staff. Dell renamed this product Distributed Private Cloud in May 2026, so both names turn up in the twin's sources. It is not the private cloud from the entry above."
     }
    },
    {
     "twin": "PhysicsFleet",
     "port": 5208,
     "name": "Fleet operations physics",
     "links": [
      {
       "kind": "scenario",
       "id": "three-node-trap",
       "title": "The 3-node trap",
       "label": "The 3-node trap",
       "how": {
        "standard": "Three nodes at FTT=1, with a node fault on day 20. The three-day exposure window passes in about a second of screen time, so do not try to catch the flag: the comparison table under the narration carries an exposure-days column, three against one on four nodes, and the event log records the day it opened and the day it closed. Press the four-node row in that table to load the second run.",
        "novice": "Three servers, and one of them breaks on day 20. The programs restart elsewhere in about two minutes, but the data has nowhere to put its second copy until the broken server is repaired three days later. Do not try to catch the red warning on screen: the table under the text has an exposure-days column, three against one, and the event log writes down the day the gap opened and the day it closed. Press the four-server row in that table to run it again."
       }
      },
      {
       "kind": "scenario",
       "id": "catalog-vs-artisanal",
       "title": "Catalog vs artisanal",
       "label": "Catalog vs artisanal",
       "how": {
        "standard": "Twelve nodes, two stacks, one control plane. Two figures on the page count different things: the quarter the second stack adds is of the monthly patch wave alone, 2.4 h becoming 3.0 h, while the table's 3.4 against 4.0 h a month is the whole rate, deploys and upkeep included. Then press the hand-built row and compare its deploy hours.",
        "novice": "Twelve servers running two software platforms from one console. Two figures on the page count different things: the extra quarter is on the monthly update round only, while the table's 3.4 against 4.0 hours a month is all the work. Then press the hand-built row to see what the same new workloads cost when nobody uses the ready-made menu."
       }
      }
     ],
     "pageTitle": "Cloud &amp; Edge Fleets &middot; Operations Simulator"
    }
   ],
   "predict": {
    "q": {
     "standard": "Private Cloud doubles its storage pool. What happens to its compute units?",
     "novice": "A private cloud buys twice as much storage. Does it also get more computing power?"
    },
    "options": [
     "They double too",
     "They go up a little",
     "Nothing: they stay the same"
    ],
    "answer": 2,
    "reveal": {
     "standard": "Nothing. Storage goes from 200 to 400 TB at growstorage and compute stays at 48 units. On a hyperconverged cluster with its drive bays full, that same need is met by adding a node, and a node brings processors whether or not you wanted them. VxRail answers that with Dynamic Nodes and vSAN Max, which separate storage from compute inside its own product line, so the contrast here is between two shapes rather than between two products.",
     "novice": "Nothing changes. Storage doubles and computing stays exactly where it was, because the two are bought separately. In an all-in-one design extra storage usually arrives with extra processors attached, although VxRail now sells options that split the two as well."
    },
    "cite": [
     "DellPrivateCloud/backend/tests/test_engine.py::test_compute_and_storage_scale_independently",
     "DellPrivateCloud/backend/tests/test_engine.py::test_nothing_scales_that_was_not_asked_for"
    ]
   },
   "checks": [
    {
     "q": {
      "standard": "How many VxRail nodes light during primary election?",
      "novice": "When the cluster picks the server that will run its manager, how many servers light up?"
     },
     "a": {
      "standard": "Exactly one, n1, which breaks the lockstep the other phases keep.",
      "novice": "One, the first server. Every other stage lights all four together; this is the one stage that does not."
     },
     "cite": [
      "DellVxRail/backend/tests/test_engine.py::test_primary_election_lights_exactly_one_node"
     ]
    },
    {
     "q": {
      "standard": "How many human actions does a NativeEdge site take?",
      "novice": "When new NativeEdge devices arrive at a site, how many times does somebody there have to do something?"
     },
     "a": {
      "standard": "One: power and a cable, at the power step. Nothing comes online until attestation establishes trust, and attestation is the longest stage.",
      "novice": "Once: plug each device into power and the network. Nothing starts running until every device has proved it is genuine, and that proof is the slowest stage of all."
     },
     "cite": [
      "DellNativeEdge/backend/tests/test_engine.py::test_exactly_one_human_action",
      "DellNativeEdge/backend/tests/test_engine.py::test_nothing_runs_before_trust_is_established",
      "DellNativeEdge/backend/tests/test_engine.py::test_attestation_is_the_longest_stage"
     ]
    },
    {
     "q": {
      "standard": "What does CloudIQ's health score do across the pipeline?",
      "novice": "What happens to CloudIQ's health score as the measurements travel through?"
     },
     "a": {
      "standard": "It starts at 100, dips to 71 at detect, and ends at 88 at notify: recovered, but not back to 100.",
      "novice": "It starts at 100, drops to 71 when the problem is found, and finishes at 88: better, but not back to perfect."
     },
     "cite": [
      "DellCloudIQ/backend/tests/test_engine.py::test_health_starts_perfect_dips_on_detection_then_recovers"
     ]
    },
    {
     "q": {
      "standard": "In the physics app, same fleet and same faults, run manually against automated: how many more admin hours does manual take?",
      "novice": "In the physics app, run the same servers with the same faults by hand and then with software. How much more time does the hand-run cost?"
     },
     "a": {
      "standard": "More than five times as many. The two runs are the VxRail ×8 automated and VxRail ×8 manual builds in the app's Build panel; read admin-hours total in the summary.",
      "novice": "More than five times as many hours. Load the two builds called VxRail ×8 automated and VxRail ×8 manual in the Build panel and compare the admin-hours total."
     },
     "cite": [
      "PhysicsFleet/backend/tests/test_engine.py::test_automation_is_an_order_of_magnitude"
     ]
    }
   ],
   "pins": [
    {
     "twin": "DellPrivateCloud",
     "step": 5,
     "field": "storage_tb",
     "value": 200
    },
    {
     "twin": "DellPrivateCloud",
     "step": 6,
     "field": "storage_tb",
     "value": 400
    },
    {
     "twin": "DellPrivateCloud",
     "step": 6,
     "field": "compute_units",
     "value": 48
    },
    {
     "twin": "DellCloudIQ",
     "step": 5,
     "field": "health_score",
     "value": 71
    },
    {
     "twin": "DellCloudIQ",
     "step": 8,
     "field": "health_score",
     "value": 88
    },
    {
     "twin": "DellNativeEdge",
     "step": 1,
     "field": "operator_actions",
     "value": 1
    },
    {
     "twin": "DellNativeEdge",
     "step": 7,
     "field": "operator_actions",
     "value": 1
    }
   ],
   "lab": {
    "twin": "PhysicsFleet",
    "port": 5208,
    "id": "headroom-for-the-last-day",
    "title": "Headroom for the last day",
    "difficulty": 1,
    "label": "Open the lab: Headroom for the last day",
    "goal": {
     "standard": "A cluster whose VMs grow every month takes a node fault early and another late. Make both faults short failovers with no open protection window, using as few nodes as you can. Protection needs somewhere to rebuild, and on the last day there is less room than on the first.",
     "novice": "A cluster keeps getting busier, and a server fails once early and once much later. Both failures should cost only a brief switch-over, with the data never left unprotected — and you should buy as few servers as possible. Rebuilding after a failure needs spare room, and the cluster has least spare room at the end."
    },
    "lever": {
     "standard": "Size against the last month's footprint plus one node's worth of rebuild capacity, not the first month's.",
     "novice": "Work out how full the cluster will be at the end, then add room for one server's worth of rebuilding."
    },
    "how": {
     "standard": "Open the Labs tab in the app, pick this lab, read its goal and constraints, and build the scenario with the controls this module already used. Run and grade replays the same pure engine and scores the trace: every constraint is measured from the trace, not taken on trust, so an idle build cannot pass. Thresholds and scores are illustrative.",
     "novice": "In the app, open the tab called Labs and choose this lab. It states a goal and some rules. Set the controls the way you think will work, then press Run and grade. The app checks what actually happened in the run, so you cannot pass by doing nothing. Change one setting at a time and grade again. The pass marks are made up for teaching, not measurements."
    },
    "cite": [
     "PhysicsFleet/backend/tests/test_labs.py::test_lab_invariants",
     "PhysicsFleet/backend/tests/test_labs.py::test_there_are_three_labs_of_rising_difficulty"
    ]
   },
   "bridge": {
    "text": {
     "standard": "One endpoint in a NativeEdge estate is a Pro Max Plus workstation running a model with no network at all. The next module opens it and returns to the roofline from the first module.",
     "novice": "One of those edge machines could be a laptop running an AI model with no internet. Next: why that works, which goes back to the very first module."
    },
    "next": "M11"
   },
   "failures": [
    {
     "twin": "DellCloudIQ",
     "port": 5180,
     "trace": "pipeline",
     "name": "CloudIQ: connected, and no data",
     "scenario": "connected-no-data",
     "at": {
      "kind": "phase",
      "value": "stale"
     },
     "label": "Connected-no-data trace, paused two hours into the silence",
     "q": {
      "standard": "The Secure Connect Gateway passes its connection test and Dell's records list the new array under your site, but a firewall or proxy rule blocks the outbound telemetry upload. What Health Score does the app show for this system two hours later, and which side can fix it?",
      "novice": "A new storage array is registered with Dell's monitoring service and the connection test passes, but a firewall rule is quietly blocking the data it tries to send. Two hours later, what health score does the service show for it?"
     },
     "options": [
      "100, because nothing bad was detected",
      "A grey dash: no score at all; only the customer side can fix it",
      "A low score, and Dell's cloud reconnects by itself"
     ],
     "answer": 1,
     "a": {
      "standard": "No number at all. A system that has never delivered data has no score: the app draws a grey dash, and the portal's Connectivity view lists the array outside Connected, because Connected means successfully sending data. The cloud does not detect this by timing the silence. A new system can take up to an hour to show data, so the dash counts as a fault only after that, and someone has to look. Analytics, cybersecurity, the Assistant and notifications stay dark throughout: no insight is generated from missing data. Only the customer side can fix it (a proxy or firewall rule, DNS, or enabling collection on the array), because every connection is opened from the customer side. After the fix the backlog flows, analysis runs, and only then does a coloured score appear. The full backfill, the refused destination and the timings are illustrative.",
      "novice": "No score at all. The service shows a grey dash, because it never gives a health score to a system it has no data from. It does not raise an alarm either; someone has to notice the dash, and a new system can take up to an hour to show data anyway. None of the clever analysis runs while there is nothing to analyse. The fix has to come from your side, such as a firewall rule, because Dell's service never opens a connection into your network. Once data flows, the saved-up readings arrive, get analysed, and then a real score appears."
     },
     "cite": [
      "DellCloudIQ/backend/tests/test_scenarios.py::test_never_a_green_score_on_no_data",
      "DellCloudIQ/backend/tests/test_scenarios.py::test_no_insight_is_ever_generated_from_missing_data",
      "DellCloudIQ/backend/tests/test_scenarios.py::test_the_fix_comes_from_the_customer_side_and_flow_stays_one_way",
      "DellCloudIQ/backend/tests/test_scenarios.py::test_nothing_collected_is_dropped"
     ],
     "pins": [
      {
       "step": 5,
       "field": "scoreState",
       "value": "no-data"
      },
      {
       "step": 5,
       "field": "minutesWithoutData",
       "value": 120
      },
      {
       "step": 5,
       "field": "dataPoints",
       "value": 0
      },
      {
       "step": 9,
       "field": "scoreState",
       "value": "fresh"
      }
     ]
    },
    {
     "twin": "DellVxRail",
     "port": 5179,
     "trace": "firstrun",
     "name": "VxRail: the fifth node with the wrong image",
     "scenario": "node-add-mismatch",
     "at": {
      "kind": "phase",
      "value": "refused"
     },
     "label": "Node-add trace, paused where VxRail Manager refuses the node",
     "q": {
      "standard": "A fifth node arrives with a factory image (7.0.370) older than the running cluster (8.0.300), and the admin clicks Add. At the moment VxRail Manager refuses the node, how many hosts are in vSAN, how big is the datastore, and what has to be rolled back on the running cluster?",
      "novice": "A cluster of four servers is running 96 virtual machines. A fifth server arrives with older software and someone tries to add it. The cluster refuses it. At that moment, what has to be undone on the running cluster?"
     },
     "options": [
      "Five hosts, 150 TB, and the vSAN claim has to be rolled back",
      "Four hosts, 120 TB, and nothing to roll back",
      "Four hosts, 120 TB, and the VMs pause while the check runs"
     ],
     "answer": 1,
     "a": {
      "standard": "Four hosts, 120 TB, and nothing to roll back. The compatibility precheck is read-only and the Add VxRail Hosts wizard applies nothing until Finish, so the refusal comes before any cluster IP, vSphere membership or vSAN disk claim, and the 96 VMs never notice. What the refusal costs is time on node 5: the RASR re-image, the longest stage. Capacity moves once, to 150 TB, after the retry's check passes. One caveat: for version pairs that Dell's Node Addition Matrix (KB 000012298) supports, recent releases level the node up during expansion instead of refusing it; this trace assumes an unsupported pair (7.0.x into 8.0.x). Versions, TB, VM count and timings are illustrative.",
      "novice": "Nothing. The check that refuses the new server only reads; it changes nothing on the running cluster. So there are still four servers sharing 120 TB, and the 96 virtual machines never notice. The cost is time on the new server, which has to have its software reinstalled to match, and that is the slowest part. Only after it passes the check a second time does it join, and the storage grows once, to 150 TB. For some version pairs Dell's tools upgrade the new server automatically instead of refusing it; this model assumes a pair where that is not supported."
     },
     "cite": [
      "DellVxRail/backend/tests/test_nodeadd.py::test_a_mismatched_node_never_joins_vsan",
      "DellVxRail/backend/tests/test_nodeadd.py::test_the_refusal_comes_before_the_node_touches_vsan",
      "DellVxRail/backend/tests/test_nodeadd.py::test_the_running_cluster_is_untouched_throughout",
      "DellVxRail/backend/tests/test_nodeadd.py::test_the_datastore_never_shrinks_and_grows_exactly_once"
     ],
     "pins": [
      {
       "step": 4,
       "field": "vsanNodes",
       "value": 4
      },
      {
       "step": 4,
       "field": "datastoreTb",
       "value": 120
      },
      {
       "step": 4,
       "field": "vmsRunning",
       "value": 96
      },
      {
       "step": 4,
       "field": "nodeVersion",
       "value": "7.0.370"
      },
      {
       "step": 4,
       "field": "clusterVersion",
       "value": "8.0.300"
      },
      {
       "step": 10,
       "field": "datastoreTb",
       "value": 150
      },
      {
       "agg": "max",
       "field": "mismatchedNodesInVsan",
       "value": 0
      }
     ]
    },
    {
     "twin": "DellNativeEdge",
     "port": 5187,
     "trace": "onboard",
     "name": "NativeEdge: one device fails attestation",
     "scenario": "attestation-fails",
     "at": {
      "kind": "phase",
      "value": "quarantine"
     },
     "label": "Attestation-fails trace, paused at the quarantine",
     "q": {
      "standard": "Four devices are plugged in at a site and one fails attestation: its firmware measurement or ownership voucher does not match. When does the site's workload start running on the other three, compared with the happy path? And how many on-site human actions does the trace count by the end?",
      "novice": "Four new devices are plugged in at a shop. One of them cannot prove it is genuine. Do the other three have to wait for it before they start working? And how many times does a person on site have to do something by the end?"
     },
     "options": [
      "Later than the happy path; one action",
      "At the same time; two actions under two names",
      "Not until the bad unit is replaced; two actions"
     ],
     "answer": 1,
     "a": {
      "standard": "At exactly the same time. Trust is a per-device verdict, so the bad unit is quarantined (3 of 4 endpoints online, nothing ever sent to it) while the healthy three onboard, take their blueprint and workload, and reach managed on the happy path's clock, before any recovery begins. The on-site count ends at two under two names: operatorActions = 1 (power and a cable) and recoveryActions = 1 (the swap). The administrator's support case with Dell is central work, described but not counted, and the replacement attests from scratch before it receives anything. Honest caveat: Dell's KB documents the voucher-mismatch event only with an Orchestrator-side cause fixed by a central script. A single device failing alone, the word quarantine, and all timings including the three-day replacement are illustrative. One reading note: the link pauses on the quarantine step itself, where devices trusted already reads 3 of 4 while endpoints online still reads 0 of 4. The Orchestrator claims those three on the next step, so press Step once to watch the counter move.",
      "novice": "They do not wait. Each device is judged separately, so the one that fails is set aside and sent nothing, while the other three are set up and start working exactly as fast as if nothing had gone wrong. By the end a person on site has acted twice: once to plug everything in, and once to swap the bad device. The replacement has to prove itself from scratch before it gets anything. The timings, including three days for the replacement to arrive, are illustrative, and the word quarantine is this model's, not Dell's. One thing to watch on screen: the link pauses at the moment the failed device is set aside, where devices trusted already says 3 of 4 but endpoints online still says 0 of 4. Press Step once and the online count moves to three."
     },
     "cite": [
      "DellNativeEdge/backend/tests/test_scenarios.py::test_one_bad_device_never_blocks_the_estate",
      "DellNativeEdge/backend/tests/test_scenarios.py::test_nothing_is_deployed_to_an_unattested_device",
      "DellNativeEdge/backend/tests/test_scenarios.py::test_human_actions_are_counted_honestly"
     ],
     "pins": [
      {
       "step": 4,
       "field": "endpointsOnline",
       "value": 3
      },
      {
       "step": 10,
       "field": "endpointsOnline",
       "value": 4
      },
      {
       "step": 10,
       "field": "operatorActions",
       "value": 1
      },
      {
       "step": 10,
       "field": "recoveryActions",
       "value": 1
      }
     ]
    }
   ]
  },
  {
   "id": "M11",
   "title": "Inference at the edge",
   "core": true,
   "idea": {
    "standard": "A model that fits in the card's own memory crosses the link once; after that the token rate is set by that memory's bandwidth, because decode is memory-bound.",
    "novice": "The whole model fits in the memory on the AI card, so it is copied there once and never sent again. From then on, how fast the answer appears depends on how fast the card can read its own memory."
   },
   "prereqs": [
    "M1"
   ],
   "background": {
    "standard": "Inference is a trained model in use: answering, rather than learning. The edge here means the machine in front of you rather than a datacenter, and this module's machine is a 16-inch laptop with an add-in inference card. Generation runs in two stages: prefill reads the whole prompt at once, then decode writes the answer one token at a time, a token being a short piece of a word. The KV cache (key and value) is the running record of everything said so far, and decode re-reads it for every new token.",
    "novice": "Inference means using an AI model that has already been trained: it answers questions rather than learning from them. The edge means the machine in front of you rather than a computer in a datacenter — here, a laptop with an extra chip inside it built only for running AI models. Answering happens in two stages. First the machine reads your whole question at once. Then it writes the answer one small piece at a time; those pieces are called tokens. While it writes, it keeps notes on everything said so far, called the KV cache, and re-reads those notes before every new piece."
   },
   "objectives": [
    {
     "standard": "Say why 61 GB of weights cross the PCIe link once and never again, and what the card's 64 GB has to do with it.",
     "novice": "Say why the model travels to the AI card one time only, and why the size of the card's memory decides it."
    },
    {
     "standard": "Connect decode to the memory-bound regime: each token re-reads a large working set for very few multiply-adds, so intensity sits below the ridge point.",
     "novice": "Explain why writing an answer is held up by fetching numbers from memory rather than by the arithmetic itself."
    },
    {
     "standard": "Separate token rate from tokens per joule, and engine watts from system watts.",
     "novice": "Tell apart how fast an engine writes and how much energy each piece of the answer costs — and see why counting the whole machine changes the second answer."
    }
   ],
   "entries": [
    {
     "twin": "DellProMaxPlus",
     "port": 5186,
     "pageTitle": "Dell Pro Max Plus Inside",
     "trace": "inference",
     "name": {
      "standard": "Pro Max Plus with a discrete NPU",
      "novice": "A laptop with an AI card inside it"
     },
     "note": {
      "standard": "The whole argument in one trace: a model compiled for this card, moved across PCIe once, and then answering with the link at zero. Watch the PCIe traffic row in the Telemetry panel throughout.",
      "novice": "This model shows the laptop loading a very large AI model onto its AI card and then answering questions. Keep an eye on the row called PCIe traffic — it is the traffic between the laptop and the card."
     },
     "links": [
      {
       "kind": "tour",
       "id": "weights-cross-once",
       "label": {
        "standard": "Guided tour, as the weights cross once",
        "novice": "Narrated walk-through, at the moment the model moves"
       },
       "how": {
        "standard": "The tour opens at the beat where 61 GB of weights stream from the SSD into the card's memory. Two beats back, Three rooms and one narrow door, lays out the host side, the card side and the PCIe strip between them, if you want the geography first.",
        "novice": "The walk-through opens at the moment the model is copied onto the card. If you would rather see the layout first, press Previous twice to reach the beat called Three rooms and one narrow door, which names the three parts and the narrow connection between them."
       }
      },
      {
       "kind": "phase",
       "value": "load",
       "label": {
        "standard": "Inference trace, at the model load",
        "novice": "The sequence, paused while the model is being copied"
       },
       "how": {
        "standard": "The Telemetry panel's PCIe traffic row reads 52 Gb/s here and 0 on every other step of the trace. The twin is honest about that figure at the higher reading levels: 52 Gb/s is about 6.5 GB/s, the shape of an SSD read rather than a PCIe ceiling, so what is modelled is the drive feeding the link. It is illustrative either way.",
        "novice": "The row called PCIe traffic reads 52 gigabits a second on this step, and zero on every other step. The number is an illustration, not a measurement."
       }
      },
      {
       "kind": "phase",
       "value": "offline",
       "label": {
        "standard": "Inference trace, with the network unplugged",
        "novice": "The last step, with the network unplugged"
       },
       "how": {
        "standard": "This is the last step. Press Back once to reach the step before it and compare the Telemetry rows — Back walks the cursor the other way, so the comparison costs nothing.",
        "novice": "This is the last step of the sequence. Press the button called Back once to see the step before it, then compare the numbers. Back moves one step backwards, so you do not have to play the whole thing again."
       }
      }
     ]
    },
    {
     "twin": "GPU",
     "port": 5173,
     "pageTitle": "GPU Matmul Visualizer",
     "name": {
      "standard": "GPU die simulator",
      "novice": "A simulator of a graphics chip"
     },
     "note": {
      "standard": "Why decode is memory-bound is easier to see on a chip than on a laptop, so the module borrows the roofline twin back for one reading. Nothing here is the Pro Max Plus; it is the same arithmetic, on a die you can watch.",
      "novice": "The reason writing an answer is slow is easier to see on this chip simulator than on the laptop, so the course comes back to it for one measurement. It is a different machine — the same idea, drawn small."
     },
     "links": [
      {
       "kind": "root",
       "label": {
        "standard": "Open the simulator, on the token-decode workload",
        "novice": "Open the chip simulator"
       },
       "how": {
        "standard": "Set Matrix size N to 8 — the flip is not visible at the default 4, where every cache length is already below the ridge — and switch the workload to LLM token decode. The controls remember their last settings, so check Precision is fp32 and Prefill is unticked. Now drag KV cache length. At 8 the token intensity reads 0.550 against a ridge point of 0.50, compute-bound; the regime turns over between 11 and 12, and by 16 it is 0.446 and memory-bound, reaching 0.313 at 64. Nothing about the die changed: the cache grew, the re-read grew, the arithmetic did not. Two regime lines sit on the page and they are scoped differently — regime (this token) grades the token being decoded, regime (whole trace) in the Roofline box grades the run — and the info dot beside the first says so. The KV length counter reads one higher than the slider, because each token appends its own key and value before it attends.",
        "novice": "First set the slider called Matrix size N to 8, then change the workload to LLM token decode, which is a model writing an answer. The controls remember what you last chose, so check Precision reads fp32 and the Prefill box is unticked. Now drag the slider called KV cache length. At 8 the line called intensity reads 0.550 and the chip is called compute-bound — busy with arithmetic. Keep dragging: around 12 it turns over, at 16 it reads 0.446 and the chip is memory-bound — waiting for data — and at 64 it reads 0.313. The chip never changed. The notes on the conversation got longer, so there is more to fetch for the same amount of arithmetic. That is the whole lesson. Two lines on the page say memory-bound or compute-bound: one grades the piece being written now, the other grades the whole run, and a small i beside the first explains why they can differ."
       }
      }
     ]
    },
    {
     "twin": "PhysicsClient",
     "port": 5204,
     "pageTitle": "Client Devices &middot; Power &amp; Thermal Simulator",
     "name": {
      "standard": "Client device physics",
      "novice": "A model of the power and heat inside a laptop"
     },
     "note": {
      "standard": "Rate and efficiency are different questions, and this is where they separate. Two honesty notes before you read the table. This build fits a 115 W GPU and the inference card in one chassis, which the Pro Max Plus twin's catalog does not offer — there the card takes the discrete GPU's place, so this is an experiment rather than a machine you can buy. And all three legs run the same ~13B-class model at the same 4-bit weight precision, so the rows compare silicon rather than quantization. That also means the card's strongest argument is missing here: the 109-billion-parameter model of the first twin, 61 GB of weights, would not fit a laptop GPU's memory at all, and a comparison every engine can run cannot show that.",
      "novice": "How fast an engine writes and how little energy it uses are two different questions, and this model separates them. Two warnings before you read the table. This laptop has both a big graphics chip and the AI card fitted at once, which you cannot order — in the real machine the card goes in the graphics chip's place, and they are put together here only so the two can be compared. And all three runs use the same medium-sized model, kept in memory the same way, so what the table compares is the chips. That leaves out the AI card's best argument: the laptop's own model from the first link, 61 gigabytes of it, would not fit inside a laptop graphics chip's memory at all, and a test that all three chips can run cannot show that."
     },
     "links": [
      {
       "kind": "scenario",
       "id": "three-engines",
       "title": "Same model, three engines",
       "label": {
        "standard": "Same model, three engines",
        "novice": "The same model run on three different chips"
       },
       "how": {
        "standard": "One battery, one model, three engines in turn: the CPU, then the GPU at t+400 s, then the NPU at t+800 s, 1200 s in all. It opens already playing at ×10 — press ×60, or drag the timeline, to reach the end of each leg. Then read Results by engine, whose columns are tok/s, tok/J engine and tok/J system. Engine watts are the chip alone; system watts are the whole machine, display and fans included, and that is the column battery life follows.",
        "novice": "The machine runs the same model on three different chips, one after another, on battery: first the ordinary processor, then the graphics chip, then the AI card. The run is twenty sim-minutes long and opens already playing at ten times speed — press ×60, or drag the timeline, to reach the end of each part. Then read the table called Results by engine. It has two columns for energy: tok/J engine counts only the chip doing the work, tok/J system counts the whole laptop. The second one is what your battery actually pays."
       }
      }
     ]
    }
   ],
   "predict": {
    "q": {
     "standard": "One laptop runs one model on its CPU, its GPU and its inference card in turn. The GPU generates the most tokens per second. Which engine gets the most tokens out of a joule?",
     "novice": "One laptop runs the same model on three different chips in turn. The graphics chip writes the answer fastest. Which chip gets the most words out of the least energy?"
    },
    "options": [
     {
      "standard": "The GPU — it is fastest, and finishing sooner spends less energy",
      "novice": "The graphics chip — it is fastest, and finishing sooner uses less energy"
     },
     {
      "standard": "About the same: the display, memory and fans dominate either way",
      "novice": "All three about the same: the screen, memory and fans use most of it anyway"
     },
     {
      "standard": "The inference card, by roughly two to one on the chip's own watts",
      "novice": "The AI card, by about two to one if you count only the chip doing the work"
     },
     {
      "standard": "The CPU, because it never leaves its sustained power limit",
      "novice": "The ordinary processor, because it never draws much power"
     }
    ],
    "answer": 2,
    "reveal": {
     "standard": "The inference card. On the chip's own watts it returns 0.75 tok/J against the GPU's 0.39, about 1.9 to one. Counted across the whole machine the lead narrows to 0.38 against 0.30, about 1.3 to one, because the display, memory, storage and fans draw power whichever chip is working — and the system figure is the one that sets battery life. Rate is a separate question, and the GPU wins it: 39.2 tok/s against 30.0, with the CPU at 6.0. All figures illustrative.",
     "novice": "The AI card. Counting only the chip doing the work, it gets about twice as many words per unit of energy as the graphics chip (0.75 against 0.39). Counting the whole laptop, its lead shrinks to about a third more (0.38 against 0.30), because the screen, memory and fans draw power whatever is working. Speed is a different question, and the graphics chip wins that one: 39.2 words a second against 30.0, with the ordinary processor far behind at 6.0. The numbers are illustrations."
    },
    "cite": [
     "PhysicsClient/backend/tests/test_engine.py::test_npu_wins_tokens_per_joule"
    ]
   },
   "checks": [
    {
     "q": {
      "standard": "Across the whole inference trace, on which steps is PCIe traffic above zero?",
      "novice": "During the whole sequence, when is there any traffic between the laptop and the AI card?"
     },
     "a": {
      "standard": "One step only: the load, at 52 Gb/s (illustrative). Every other step reads 0, including all of decode. The weights are never evicted either — resident holds at 61 GB of the card's 64 GB from the load onwards.",
      "novice": "Only once, while the model is being copied across. After that the traffic row reads zero for the rest of the sequence, including every step where the machine is writing an answer. The model stays on the card: 61 gigabytes of its 64."
     },
     "cite": [
      "DellProMaxPlus/backend/tests/test_engine.py::test_weights_cross_the_link_exactly_once",
      "DellProMaxPlus/backend/tests/test_engine.py::test_weights_are_monotonic_and_never_evicted"
     ]
    },
    {
     "q": {
      "standard": "What changes at the final offline step, when the network is unplugged? Compare it with the step before, using Back.",
      "novice": "The last step unplugs the network. What changes? Press Back once to see the step before it and compare."
     },
     "a": {
      "standard": "Nothing. Generation rate stays at 21 tok/s and card power at 67 W, the same as the step before; PCIe traffic was already 0. Nothing after the load depended on anything outside the chassis, so there is nothing for the network to take away.",
      "novice": "Nothing at all. The answer is still being written at 21 pieces a second and the card still draws 67 watts, exactly as on the step before. Nothing after the model was loaded needed anything outside the laptop."
     },
     "cite": [
      "DellProMaxPlus/backend/tests/test_engine.py::test_disconnecting_the_network_changes_nothing"
     ]
    },
    {
     "q": {
      "standard": "Why is decode memory-bound, and what does lengthening the KV cache do to the number that settles it?",
      "novice": "Why is writing the answer limited by memory rather than by arithmetic, and what happens when the model's notes get longer?"
     },
     "a": {
      "standard": "Each token re-reads a large working set — the active weights plus the KV cache, the record of the conversation so far — for very few multiply-adds, so arithmetic intensity falls below the die's ridge point. Lengthening the cache pushes it down: on the simulator at N 8, token intensity reads 0.550 at a cache of 8, above the 0.50 ridge and compute-bound, and 0.446 at 16 and 0.313 at 64, memory-bound. A long conversation is what moves a decode step across the ridge, and the die never changed.",
      "novice": "To write each piece of the answer the chip has to read a lot of numbers — part of the model, plus all the notes it has kept on the conversation — and then do very little arithmetic with them, so it spends its time fetching. The longer the notes, the worse that gets. On the simulator the ratio starts at 0.550, above the chip's break-even of 0.50, and falls to 0.446 and then 0.313 as the notes grow. A long conversation is what tips it over, not a different chip."
     },
     "cite": [
      "GPU/backend/tests/test_llm.py::test_intensity_pinned_fall_and_monotone_decrease",
      "GPU/backend/tests/test_llm.py::test_regime_flips_across_the_ridge"
     ]
    }
   ],
   "pins": [
    {
     "twin": "DellProMaxPlus",
     "step": 2,
     "field": "link_gbps",
     "value": 52
    },
    {
     "twin": "DellProMaxPlus",
     "step": 5,
     "field": "link_gbps",
     "value": 0
    },
    {
     "twin": "DellProMaxPlus",
     "step": 6,
     "field": "tokens_per_second",
     "value": 21
    },
    {
     "twin": "DellProMaxPlus",
     "step": 7,
     "field": "tokens_per_second",
     "value": 21
    },
    {
     "twin": "DellProMaxPlus",
     "step": 6,
     "field": "npu_watts",
     "value": 67
    },
    {
     "twin": "DellProMaxPlus",
     "step": 7,
     "field": "npu_watts",
     "value": 67
    },
    {
     "twin": "DellProMaxPlus",
     "step": 7,
     "field": "weights_resident_gb",
     "value": 61
    }
   ],
   "scenarioPins": [
    {
     "twin": "PhysicsClient",
     "scenario": "three-engines",
     "step": 799,
     "field": "tokensPerS",
     "value": 39.2,
     "tol": 0.05
    },
    {
     "twin": "PhysicsClient",
     "scenario": "three-engines",
     "step": 799,
     "field": "tokensPerJoule",
     "value": 0.39,
     "tol": 0.005
    },
    {
     "twin": "PhysicsClient",
     "scenario": "three-engines",
     "step": 799,
     "field": "systemTokensPerJoule",
     "value": 0.3,
     "tol": 0.005
    },
    {
     "twin": "PhysicsClient",
     "scenario": "three-engines",
     "step": -1,
     "field": "tokensPerS",
     "value": 30.0,
     "tol": 0.05
    },
    {
     "twin": "PhysicsClient",
     "scenario": "three-engines",
     "step": -1,
     "field": "tokensPerJoule",
     "value": 0.75,
     "tol": 0.005
    },
    {
     "twin": "PhysicsClient",
     "scenario": "three-engines",
     "step": -1,
     "field": "systemTokensPerJoule",
     "value": 0.38,
     "tol": 0.005
    },
    {
     "twin": "PhysicsClient",
     "scenario": "three-engines",
     "step": 399,
     "field": "tokensPerS",
     "value": 6.0,
     "tol": 0.05
    }
   ],
   "lab": {
    "twin": "PhysicsClient",
    "port": 5204,
    "id": "charge-while-you-play",
    "title": "Charge while you play",
    "difficulty": 1,
    "label": "Open the lab: Charge while you play",
    "goal": {
     "standard": "A half-hour session from a low pack: deliver compute throughout and still finish charged, with the battery never discharging and nothing throttling. The supply identity this module used is the constraint — adapter plus battery equals system plus charge, and the charge term is what is left over.",
     "novice": "The laptop starts with a nearly empty battery and has half an hour of work to do. It must do real work the whole time, must never run the battery down while plugged in, must not get so hot that it slows itself, and must end up much more charged than it started. Whatever the charger has left after running the machine is what goes into the battery."
    },
    "lever": {
     "standard": "The adapter is a hard ceiling; thermal mode and the load dials decide how much of it the system takes, and the remainder is the charge rate.",
     "novice": "The charger can only give so much. Everything the machine uses comes off the top, and the rest charges the battery."
    },
    "how": {
     "standard": "Open the Labs tab in the app, pick this lab, read its goal and constraints, and build the scenario with the controls this module already used. Run and grade replays the same pure engine and scores the trace: every constraint is measured from the trace, not taken on trust, so an idle build cannot pass. Thresholds and scores are illustrative.",
     "novice": "In the app, open the tab called Labs and choose this lab. It states a goal and some rules. Set the controls the way you think will work, then press Run and grade. The app checks what actually happened in the run, so you cannot pass by doing nothing. Change one setting at a time and grade again. The pass marks are made up for teaching, not measurements."
    },
    "cite": [
     "PhysicsClient/backend/tests/test_labs.py::test_lab_invariants",
     "PhysicsClient/backend/tests/test_labs.py::test_there_are_three_labs_of_rising_difficulty"
    ]
   },
   "bridge": {
    "text": {
     "standard": "The Pro Max Plus wins by refusing to move data. An AI factory cannot refuse: its data has to arrive, and when it does not, every other module's hardware waits. The capstone couples them all.",
     "novice": "The laptop wins by never moving its data. A giant AI factory has to move data all the time, and when data is late, everything waits. The last module puts all the pieces together."
    },
    "next": "M12"
   }
  },
  {
   "id": "M12",
   "title": "Capstone: stand up an AI factory",
   "core": true,
   "idea": {
    "standard": "GPUs sit idle because data did not arrive, and that coupling decides the whole factory.",
    "novice": "In an AI factory the expensive GPUs often sit waiting because the data is late. That link between parts decides how well the whole place works."
   },
   "prereqs": [
    "M4",
    "M5",
    "M7",
    "M8"
   ],
   "background": {
    "standard": "Everything so far; the security module is recommended. Two words the compute map leads with, which no earlier module defines: an eight-GPU server carries its GPUs on an HGX baseboard, NVIDIA's carrier board, in a bolted-down socket called SXM that lets one chip draw far more power than a plug-in card could. The instruments read DC power (what the machine draws after its supplies have converted the wall's alternating current) and wall or busbar power (what the building pays for, the busbar being the rack's DC power rail). On the factory dashboard, PUE is building power divided by IT power, MTBF is mean time between failures, a checkpoint is a saved copy of the training state, and $ per million tokens divides energy plus amortized capex — the purchase price of the racks spread over their service life — by the tokens produced so far.",
    "novice": "Everything so far; the security module is recommended. Two words the compute picture opens with: the eight graphics chips in an AI server sit on one carrier board, which NVIDIA calls HGX, in a bolted-down socket called SXM that lets each chip draw far more power than a plug-in card could. The meters show DC power, which is what the machine itself draws, and wall power, which is what the building is billed for. On the factory dashboard, PUE is total building power divided by computer power, MTBF is the average time between breakdowns, a checkpoint is a saved copy of the half-trained model, and the cost tile spreads the price of the racks over their working life and adds the electricity, then divides by the work done so far."
   },
   "objectives": [
    {
     "standard": "Reason from coupled subsystems to the six headline instruments.",
     "novice": "Follow how one part of the factory changes the six big numbers on the dashboard."
    },
    {
     "standard": "Show that starvation, checkpoint cost and the power budget come out of the trace rather than being set as parameters.",
     "novice": "Show that waiting GPUs, the cost of saving work, and the power limit all fall out of the model rather than being typed in."
    },
    {
     "standard": "Map a real deployment onto the modules, and say which blocks the public sources do not cover.",
     "novice": "Match a real data centre to the models you have played, and notice which parts the public reports say nothing about."
    }
   ],
   "entries": [
    {
     "twin": "PhysicsAIFactory",
     "port": 5219,
     "pageTitle": "Dell AI Factory — Capstone Simulator",
     "name": "AI factory capstone",
     "note": {
      "standard": "Two clocks, and they are not the same clock. The six tiles across the top follow the playback cursor; the Run summary on the right is computed over the whole run and is filled in before you press play. The cursor is an hour: the slider under the transport buttons reads hour N of 480, and every question below asks for an hour, not a day.",
      "novice": "Two sets of numbers, and they do not mean the same thing. The six big tiles at the top follow wherever you have paused. The Run summary on the right is the total for the whole run and is already filled in before you press play. The slider under the play buttons says which hour you are on; every question here asks for an hour."
     },
     "links": [
      {
       "kind": "scenario",
       "id": "stand-up",
       "title": "Stand up an AI factory",
       "label": "Stand up an AI factory",
       "how": {
        "standard": "Drag the scrubber to hour 112 — the first training token. Tokens per second sat at zero for every hour before it while the cost tile kept charging: about $78 k by then, all of it hardware amortization. Ask yourself which of the three waits (72 h procurement, 2 h per rack to install, 24 h of bring-up) you would shorten first.",
        "novice": "Drag the slider to hour 112, the moment the first work gets done. Nothing was produced before that, but the cost meter was running the whole time: about $78 k spent before a single token. Three waits make up those 112 hours — getting the hardware, installing the racks, and testing. Which would you shorten?"
       }
      },
      {
       "kind": "scenario",
       "id": "starved-cluster",
       "title": "The starved cluster",
       "label": "The starved cluster",
       "how": {
        "standard": "Pause at hour 249, note tokens per second, facility MW and $ / Mtok, then move to hour 300 and read the same three. Tokens fall 33,173 → 11,514 per second; facility power falls only 0.90 → 0.69 MW; the cost tile moves 11.42 → 12.19 and reaches 13.85 by hour 480. The cost tile is a running average over the whole run so far, so it drifts rather than steps — the answer below works out what the hour-by-hour cost really did.",
        "novice": "Pause at hour 249 and write down the three numbers: work per second, building power, and cost per million words. Then move to hour 300 and read them again. The work more than halves, the power barely moves, and the cost creeps up rather than jumping, because that tile is an average of the whole run so far."
       }
      },
      {
       "kind": "scenario",
       "id": "checkpoint-goldilocks",
       "title": "Checkpoint Goldilocks",
       "label": "Checkpoint Goldilocks",
       "how": {
        "standard": "Set the checkpoint interval in the build panel to 5, then 60, then 480 minutes, and read tokens produced in the Run summary each time: 187.7 B, 190.5 B, 182.7 B. Leave it at 480 to watch the event log, which is the only place in this app where a rollback is visible.",
        "novice": "Set the saving interval in the build panel to 5 minutes, then 60, then 480, and read tokens produced in the Run summary each time: 187.7, 190.5, 182.7 billion. Leave it at 480 and watch the event log — this is the one place where you can see work being thrown away."
       }
      },
      {
       "kind": "scenario",
       "id": "warm-day",
       "title": "Warm day at 90% of budget",
       "label": "Warm day at 90% of budget",
       "how": {
        "standard": "Watch the facility tile flip to CAPPED at hour 250 and back at hour 350; the log marks both. Then make the counterfactual the page does not show: note tokens produced (140.4 B), raise the facility budget slider to 1.05 MW, and read it again (142.8 B, nothing capped).",
        "novice": "Watch the building-power tile say CAPPED from hour 250 to hour 350; the log marks both moments. The page never shows you what would have happened otherwise, so make it yourself: note tokens produced (140.4 billion), then raise the facility budget slider to 1.05 MW and read it again (142.8 billion, nothing capped)."
       }
      }
     ]
    },
    {
     "twin": "PhysicsCompute",
     "port": 5205,
     "pageTitle": "AI Compute &middot; Power &amp; Thermal Simulator",
     "name": "AI compute physics",
     "note": {
      "standard": "The same starvation one machine down, where it is measured in watts rather than megawatts. The header's kW figure is DC power, and it is still climbing when the page opens: about 7.35 kW on arrival, settling near 7.6 kW once the fans have ramped. After the data feed is cut it falls to about 5.5 kW while tokens per second fall 960 → 288 — and roughly 340 W of that fall is fans slowing down, not GPUs computing less.",
      "novice": "The same starvation inside one machine, where the numbers are in kilowatts instead of megawatts. The kW in the header is what the machine draws, and it is still rising as the page opens: about 7.35 kW at first, settling near 7.6 kW once the fans are up to speed. After the data is cut it drops to about 5.5 kW while the work falls from 960 to 288 per second — and a good part of that drop is the fans slowing, not the chips doing less."
     },
     "links": [
      {
       "kind": "scenario",
       "id": "starved",
       "title": "Starved GPUs",
       "label": "Starved GPUs",
       "how": {
        "standard": "Let it run past the cut at t+300 s and compare the header before and after. Turn Explain mode on and read the power-chain card under DC power, wall / busbar and GPU power: it is the tile group this comparison rests on.",
        "novice": "Let it play past the moment the data is cut, about five minutes in, and compare the header before and after. Turn Explain mode on and read the card under the power numbers — it explains what DC power and wall power mean."
       }
      }
     ]
    },
    {
     "twin": "CustomerSetup",
     "name": "Real deployments drawn with the twins",
     "links": [
      {
       "kind": "setup",
       "path": "xAI-Colossus/setup.html",
       "label": "xAI Colossus"
      },
      {
       "kind": "setup",
       "path": "TACC-Horizon/setup.html",
       "label": "TACC Horizon"
      }
     ]
    }
   ],
   "predict": {
    "q": {
     "standard": "Storage delivers half the data the GPUs demand. What happens to tokens per second, and what happens to power?",
     "novice": "The storage can only deliver half the data the GPUs want. What happens to the amount of work done, and to the electricity bill?"
    },
    "options": [
     "Both fall by half",
     "Tokens fall by about half; power barely falls",
     "Tokens hold, because GPUs queue the work"
    ],
    "answer": 1,
    "reveal": {
     "standard": "Tokens per second fall with the supply and GPU idle due to data rises to match. Power does not follow: a starved GPU busy-waits and still draws most of its power, which is where the waste comes from. In the twin's own run the cut is deeper than half — 33,173 → 11,514 tokens per second, idle 65% — while facility power falls only 0.90 → 0.69 MW. Read the cost consequence carefully: the $ / Mtok tile is a running average over the whole run so far, so it only drifts from $11.42 at hour 249 to $13.85 by hour 480. The hour-by-hour cost nearly triples. Before the cut the factory spends about $757 an hour (0.898 MW at $0.08/kWh, plus eight racks at $3.0 M over four years) for 119 Mtok an hour, or $6.34 per million; after it, about $740 an hour for 41 Mtok, or $17.86. Take the tile's $11.4 → $13.9 into a capacity plan and you understate the cost of under-provisioning storage by roughly three times. All dollar figures here are illustrative.",
     "novice": "The work drops as far as the data does, and the GPUs spend the rest of their time waiting. The electricity bill barely moves, because a waiting GPU still uses most of its power — that is the waste. In the model's own run the work falls from 33,173 to 11,514 per second while building power falls only from 0.90 to 0.69 MW. Be careful with the cost tile: it is an average of the whole run so far, so it creeps from $11.42 to $13.85 and hides how bad the change was. Hour by hour, the real cost of the work goes from about $6.34 per million to about $17.86 — nearly three times worse. The dollar figures are made up for teaching."
    },
    "cite": [
     "PhysicsAIFactory/backend/tests/test_engine.py::test_starvation_emerges_from_the_arithmetic",
     "PhysicsAIFactory/backend/tests/test_engine.py::test_starvation_cuts_tokens_far_more_than_power",
     "PhysicsCompute/backend/tests/test_engine.py::test_data_starvation_cuts_tokens_more_than_watts"
    ]
   },
   "checks": [
    {
     "q": {
      "standard": "Checkpoint every 5, 60 or 480 minutes: which run finishes with the most tokens, and why does the build panel's own optimum of about 29 minutes not beat it?",
      "novice": "Save the work every 5, 60 or 480 minutes: which run ends with the most done, and why does the panel's suggestion of about 29 minutes not do better?"
     },
     "a": {
      "standard": "60 minutes, at 190.5 B, against 187.7 B at 5 and 182.7 B at 480. Saving every five minutes taxes every training hour; saving every eight hours throws away up to eight hours of work at each failure. The panel computes a Young/Daly optimum near 29 minutes and warns when you stray far from it, but 29 scores 190.2 B — a shade below 60 — because this engine advances in whole hours, so any rollback shorter than an hour rounds away and every interval at or under 60 minutes scores the same within noise. The panel's own warning text says so.",
      "novice": "60 minutes wins, with 190.5 billion, against 187.7 at 5 minutes and 182.7 at 480. Saving every five minutes costs you time in every hour of training; saving every eight hours means each breakdown throws away up to eight hours. The panel suggests about 29 minutes and it is not wrong — 29 scores 190.2 billion — but this model counts in whole hours, so anything under an hour looks the same to it."
     },
     "cite": [
      "PhysicsAIFactory/backend/tests/test_engine.py::test_checkpoint_goldilocks_interior_optimum"
     ]
    },
    {
     "q": {
      "standard": "On the warm day, can facility power exceed the budget, and what did the warm spell cost?",
      "novice": "On the warm day, can the building use more power than it is allowed, and what did the warm spell cost?"
     },
     "a": {
      "standard": "No. The engine sheds GPU clocks so facility power sits exactly on the 0.95 MW ceiling — 99 capped hours, the tile reading CAPPED, and the log marking hour 250 and hour 350. The page shows no counterfactual, so build one: the run finishes at 140.4 B tokens, and the same run with the facility budget raised to 1.05 MW finishes at 142.8 B with nothing capped. The warm spell cost about 2.5 B tokens, and 1.05 MW is the headroom that would have made it free.",
      "novice": "No. The model slows the GPUs down until the building sits exactly on its 0.95 MW limit — 99 hours of it, with the tile reading CAPPED and the log marking hour 250 and hour 350. The page never shows what would have happened otherwise, so try it: the run ends at 140.4 billion, and the same run with the budget raised to 1.05 MW ends at 142.8 billion with nothing held back. The warm spell cost about 2.5 billion, and 1.05 MW would have made it free."
     },
     "cite": [
      "PhysicsAIFactory/backend/tests/test_engine.py::test_facility_never_exceeds_budget",
      "PhysicsAIFactory/backend/tests/test_engine.py::test_warm_day_sheds_load_and_logs_it"
     ]
    },
    {
     "q": {
      "standard": "Where does the dice roll for GPU failures happen, and in which run can you actually watch work being lost?",
      "novice": "Where does the model roll dice to decide when a GPU breaks, and in which run can you see the lost work?"
     },
     "a": {
      "standard": "Nowhere: failures arrive on MTBF arithmetic — 50,000 hours per GPU over 576 GPUs, so one about every 87 hours, landing at hours 199, 286, 373 and 460 of a 480-hour run and at the same hours every time. The engine is not allowed to import random. Lost work is only visible in Checkpoint Goldilocks, which saves every 480 minutes: its log reads 2.39 B tokens rolled back, then 1.99, 1.59, 1.19, 0.80 — shrinking by arithmetic rather than luck, because 87 hours is not a whole number of 8-hour saves and each failure lands an hour closer to its save. The starved-cluster run saves every 60 minutes, so its rollbacks are shorter than the engine's one-hour tick: the log says the loss rounds away and the token total never dips. Looking for a dip there and not finding one is the expected result, not a bug.",
      "novice": "Nowhere. Breakdowns are worked out by division, not chance: one GPU fails on average every 50,000 hours, there are 576 of them, so one breaks about every 87 hours — hours 199, 286, 373 and 460, the same in every run. You can only see work being thrown away in Checkpoint Goldilocks, which saves every eight hours: its log shows 2.39 billion lost, then 1.99, 1.59, 1.19, 0.80. In the starved-cluster run the saving happens every hour, and the model counts in whole hours, so the losses are too small to show and the total never dips. That is expected, not a fault."
     },
     "cite": [
      "PhysicsAIFactory/backend/tests/test_engine.py::test_failures_arrive_on_the_mtbf_schedule_and_roll_back_tokens",
      "PhysicsAIFactory/backend/tests/test_engine.py::test_rollback_log_agrees_with_the_token_counter"
     ]
    }
   ],
   "pins": [],
   "scenarioPins": [
    {
     "twin": "PhysicsAIFactory",
     "scenario": "starved-cluster",
     "step": 249,
     "field": "tokensPerS",
     "value": 33173,
     "tol": 5
    },
    {
     "twin": "PhysicsAIFactory",
     "scenario": "starved-cluster",
     "step": 300,
     "field": "tokensPerS",
     "value": 11514,
     "tol": 5
    },
    {
     "twin": "PhysicsAIFactory",
     "scenario": "starved-cluster",
     "step": 249,
     "field": "facilityMw",
     "value": 0.9,
     "tol": 0.01
    },
    {
     "twin": "PhysicsAIFactory",
     "scenario": "starved-cluster",
     "step": 300,
     "field": "facilityMw",
     "value": 0.69,
     "tol": 0.01
    },
    {
     "twin": "PhysicsAIFactory",
     "scenario": "starved-cluster",
     "step": 249,
     "field": "usdPerMtok",
     "value": 11.42,
     "tol": 0.02
    },
    {
     "twin": "PhysicsAIFactory",
     "scenario": "starved-cluster",
     "step": 300,
     "field": "usdPerMtok",
     "value": 12.19,
     "tol": 0.02
    },
    {
     "twin": "PhysicsAIFactory",
     "scenario": "starved-cluster",
     "step": -1,
     "field": "usdPerMtok",
     "value": 13.85,
     "tol": 0.02
    },
    {
     "twin": "PhysicsAIFactory",
     "scenario": "starved-cluster",
     "step": 300,
     "field": "gpuIdleDataPct",
     "value": 65.3,
     "tol": 0.2
    },
    {
     "twin": "PhysicsAIFactory",
     "scenario": "stand-up",
     "step": 112,
     "field": "costUsdM",
     "value": 0.078,
     "tol": 0.002
    },
    {
     "twin": "PhysicsAIFactory",
     "scenario": "stand-up",
     "step": 111,
     "field": "tokensPerS",
     "value": 0,
     "tol": 0.01
    },
    {
     "twin": "PhysicsAIFactory",
     "scenario": "checkpoint-goldilocks",
     "step": -1,
     "field": "tokensTotalB",
     "value": 182.7,
     "tol": 0.05
    },
    {
     "twin": "PhysicsAIFactory",
     "scenario": "checkpoint-goldilocks",
     "step": -1,
     "field": "tokensTotalB",
     "value": 190.5,
     "tol": 0.05,
     "patch": {
      "config": {
       "resilience": {
        "checkpointIntervalMin": 60
       }
      }
     }
    },
    {
     "twin": "PhysicsAIFactory",
     "scenario": "checkpoint-goldilocks",
     "step": -1,
     "field": "tokensTotalB",
     "value": 187.7,
     "tol": 0.05,
     "patch": {
      "config": {
       "resilience": {
        "checkpointIntervalMin": 5
       }
      }
     }
    },
    {
     "twin": "PhysicsAIFactory",
     "scenario": "checkpoint-goldilocks",
     "step": -1,
     "field": "tokensTotalB",
     "value": 190.18,
     "tol": 0.05,
     "patch": {
      "config": {
       "resilience": {
        "checkpointIntervalMin": 29
       }
      }
     }
    },
    {
     "twin": "PhysicsAIFactory",
     "scenario": "warm-day",
     "step": -1,
     "field": "tokensTotalB",
     "value": 140.36,
     "tol": 0.05
    },
    {
     "twin": "PhysicsAIFactory",
     "scenario": "warm-day",
     "step": -1,
     "field": "tokensTotalB",
     "value": 142.84,
     "tol": 0.05,
     "patch": {
      "config": {
       "facility": {
        "mwBudget": 1.05
       }
      }
     }
    },
    {
     "twin": "PhysicsAIFactory",
     "scenario": "warm-day",
     "step": 260,
     "field": "powerCapped",
     "value": true
    },
    {
     "twin": "PhysicsAIFactory",
     "scenario": "warm-day",
     "step": 260,
     "field": "facilityMw",
     "value": 0.95,
     "tol": 0.005
    },
    {
     "twin": "PhysicsCompute",
     "scenario": "starved",
     "step": 30,
     "field": "dcPowerW",
     "value": 7354,
     "tol": 5
    },
    {
     "twin": "PhysicsCompute",
     "scenario": "starved",
     "step": 250,
     "field": "dcPowerW",
     "value": 7624,
     "tol": 5
    },
    {
     "twin": "PhysicsCompute",
     "scenario": "starved",
     "step": 400,
     "field": "dcPowerW",
     "value": 5522,
     "tol": 5
    },
    {
     "twin": "PhysicsCompute",
     "scenario": "starved",
     "step": 250,
     "field": "tokensPerS",
     "value": 960,
     "tol": 1
    },
    {
     "twin": "PhysicsCompute",
     "scenario": "starved",
     "step": 400,
     "field": "tokensPerS",
     "value": 288,
     "tol": 1
    },
    {
     "twin": "PhysicsCompute",
     "scenario": "starved",
     "step": 250,
     "field": "fanPowerW",
     "value": 387,
     "tol": 3
    },
    {
     "twin": "PhysicsCompute",
     "scenario": "starved",
     "step": 400,
     "field": "fanPowerW",
     "value": 48,
     "tol": 3
    }
   ],
   "lab": {
    "twin": "PhysicsAIFactory",
    "port": 5219,
    "id": "feed-the-worst-day",
    "title": "Feed the cluster on its worst day",
    "difficulty": 1,
    "label": "Open the lab: Feed the cluster on its worst day",
    "goal": {
     "standard": "Sixteen racks behind a data platform sized to feed them exactly — until, mid-run, the platform loses half its throughput and keeps it. Size the platform so no GPU ever waits for data, deliver real work, and buy no more storage than that worst day needs. This is the capstone's hero counter as a purchasing decision.",
     "novice": "A large cluster is fed data by a storage platform that is exactly big enough — and then, part way through, half of it stops working and never comes back. Make sure the chips never sit waiting for data, keep real work coming out, and do not buy more storage than that bad day actually requires."
    },
    "lever": {
     "standard": "Headroom bought before the failure is the only headroom there is; idle-due-to-data is the metric that prices it.",
     "novice": "The only spare capacity you get is the capacity you bought in advance. Watch the gauge that says how much of the time the chips are idle waiting for data."
    },
    "how": {
     "standard": "Open the Labs tab in the app, pick this lab, read its goal and constraints, and build the scenario with the controls this module already used. Run and grade replays the same pure engine and scores the trace: every constraint is measured from the trace, not taken on trust, so an idle build cannot pass. Thresholds and scores are illustrative.",
     "novice": "In the app, open the tab called Labs and choose this lab. It states a goal and some rules. Set the controls the way you think will work, then press Run and grade. The app checks what actually happened in the run, so you cannot pass by doing nothing. Change one setting at a time and grade again. The pass marks are made up for teaching, not measurements."
    },
    "cite": [
     "PhysicsAIFactory/backend/tests/test_labs.py::test_lab_invariants",
     "PhysicsAIFactory/backend/tests/test_labs.py::test_there_are_three_labs_of_rising_difficulty"
    ]
   },
   "couplings": {
    "twin": "compose",
    "port": 5221,
    "chain": "factory-fed",
    "ids": [
     "c1",
     "c2",
     "c3",
     "c4",
     "c8"
    ],
    "seams": [
     "c1",
     "c2",
     "c3",
     "c4"
    ],
    "cite": [
     "compose/tests/test_c8.py::test_fed_and_aggregate_agree_when_nothing_is_wrong",
     "compose/tests/test_determinism.py::test_every_preset_chain_is_deterministic_and_its_seams_hold"
    ],
    "text": {
     "standard": "Every module until now has carried one number across by hand: the rack's liquid watts into the CDU, the CDU's cap back into the rack, the storage platform's delivery into the GPUs' data feed, a gray link into lost tokens. The compose app makes that carry a piece of code with a test on it — one engine's trace becomes the next engine's scenario, and an identity is asserted across the seam. The chain that ends this course is the AI factory fed by real engines rather than by its own first-order aggregates: the capstone's headline instruments, computed from the same traces you have been reading all along.",
     "novice": "Until now you have carried a number from one model to the next in your head: the heat the rack makes becomes the heat the cooling unit has to remove, and so on. The compose app does that carrying in code, and checks each hand-off — nothing is lost or invented in between. The last chain runs the AI factory from the other models' own results instead of its own rough estimates, so the big dashboard is built out of the small models you already know."
    },
    "how": {
     "standard": "Open the chain, read the seam table, and check the identity column: each row is a coupling with a stated tolerance and a pytest case that holds it. Then open the same chain on its bad day and watch which instrument moves first — the coupled chain is the only place in the course where a cooling decision and a token count are the same computation.",
     "novice": "Open the chain and look at the table of hand-offs. Each row says what was passed, how closely the two sides agree, and which test checks it. Then run the bad-day version and watch which number moves first."
    }
   },
   "bridge": {
    "text": {
     "standard": "Reopen the Colossus page with the modules behind you. The dashboard draws six blocks, and the drawing maps five of them: compute is the XE9680 and XE9712 racks, fabric the SN6000 leaf/spine, data the Exascale tier, cooling the IR7000 loop, and power the reported ~150 MW grid feed with Tesla Megapack buffering during the build-out. The sixth, resilience, has no counterpart there: checkpoint intervals and failure rates are not something the public sources report, which is why two of the checks above had to be answered from the simulator instead. The page's note box separates what the sources state from what the drawing invents, and that habit is the last lesson.",
     "novice": "Now open the Colossus page again. You have played every model it links to. Five of the dashboard's six blocks are on that drawing: the compute racks, the network, the storage, the cooling, and the power feed (about 150 MW from the grid, with Tesla battery packs smoothing the build-out). The sixth, the saving-and-recovering part, is not there at all — nobody has published how often that cluster saves its work, which is why two of the questions above had to be answered inside the simulator. Notice how the page separates facts from drawings; keeping those apart is the last lesson."
    },
    "next": null
   }
  },
  {
   "id": "E1",
   "title": "Rack power: the runtime the battery really has",
   "core": false,
   "idea": {
    "standard": "A UPS front panel's runtime is a calculation; a self-test is the only thing that checks it against the pack.",
    "novice": "The time-left number on a backup battery is a sum the unit works out. A real test is the only thing that checks that sum."
   },
   "prereqs": [],
   "background": {
    "standard": "A rack PDU is the strip a rack's kit plugs into, fed from one of the three phases of the building supply. A UPS is a battery between the utility and the rack; VRLA is the sealed lead-acid chemistry most rack UPSs use. A self-test is the UPS discharging its own pack on purpose to find out what it still holds.",
    "novice": "The machines in a rack plug into a power strip called a PDU. A building's electricity arrives on three separate supply lines, called phases, and each strip feeds from one of them. Between the wall and the rack sits a UPS: a battery that carries the rack when the power fails. Its battery is a sealed lead type that fades over the years. A self-test is the UPS running on that battery on purpose, to find out how much is left in it."
   },
   "objectives": [],
   "entries": [
    {
     "twin": "PhysicsRackPower",
     "port": 5217,
     "pageTitle": "Rack PDU &amp; UPS Physics Simulator",
     "name": "Rack PDU and UPS physics",
     "links": [
      {
       "kind": "scenario",
       "id": "old-batteries",
       "title": "The 4-year-old batteries",
       "label": "The 4-year-old batteries",
       "how": {
        "standard": "The utility fails a minute into a 15-minute run; use a faster speed. The UPS panel carries two runtime readouts side by side — read both, and the equation under them. The figures are the simulator's estimates.",
        "novice": "The power goes out one minute into the run, so press a faster speed. The battery panel shows two different time-left numbers next to each other; read both. The numbers are the simulator's estimates."
       }
      },
      {
       "kind": "scenario",
       "id": "self-test-truth",
       "title": "The self-test that told the truth",
       "label": "The self-test that told the truth"
      }
     ]
    }
   ],
   "predict": {
    "q": {
     "standard": "A four-year-old VRLA pack is on battery after a utility failure. Is the runtime on the front panel too high, too low, or right?",
     "novice": "The power goes out and an old backup battery takes over. Is the time-left number on its screen too high, too low, or right?"
    },
    "options": [
     "Too high",
     "Too low",
     "Right"
    ],
    "answer": 0,
    "reveal": {
     "standard": "Too high. The panel predicts from nameplate capacity; the faded pack delivers a fraction of it, and actual over predicted equals the capacity fraction.",
     "novice": "Too high. The screen assumes the battery is new. It is not, and it runs out early."
    },
    "cite": [
     "PhysicsRackPower/backend/tests/test_engine.py::test_old_batteries_runtime_gap_is_the_capacity_fraction"
    ]
   },
   "checks": [
    {
     "q": {
      "standard": "After four VRLA years, is the pack above or below 80% of nameplate?",
      "novice": "After four years, does the battery still hold more or less than 80% of what its label says?"
     },
     "a": {
      "standard": "Below. The twin's test requires the capacity fraction to be under 0.8, and the front panel's runtime is high by that same fraction.",
      "novice": "Less. The battery has faded to under 80% of its printed capacity, and the time-left number on the screen is too big by exactly that much."
     },
     "cite": [
      "PhysicsRackPower/backend/tests/test_engine.py::test_old_batteries_runtime_gap_is_the_capacity_fraction"
     ]
    },
    {
     "q": {
      "standard": "Moving loads between phases: does it change the total power?",
      "novice": "If you move some machines from one supply line to another, does the rack use more electricity in total?"
     },
     "a": {
      "standard": "No. It changes the imbalance between the three phases and relieves phase A; the PDU input watts are unchanged.",
      "novice": "No. The total is the same. What changes is how evenly the three supply lines share it, which is what takes the strain off the busiest one."
     },
     "cite": [
      "PhysicsRackPower/backend/tests/test_engine.py::test_balance_the_phases_moves_conserve_and_relieve"
     ]
    }
   ],
   "pins": [],
   "lab": {
    "twin": "PhysicsRackPower",
    "port": 5217,
    "id": "three-feeds-eight-servers",
    "title": "Three feeds, eight unequal servers",
    "difficulty": 1,
    "label": "Open the lab: Three feeds, eight unequal servers",
    "goal": {
     "standard": "Eight unequal servers share three phases. Dealt out in order, one phase sits well past the continuous-load line. Re-plug them so every phase stays inside the rule, then get the imbalance as low as it will go — moving a load changes which phase carries it, never the total.",
     "novice": "Eight servers of different sizes are plugged into three electrical circuits. Done in the obvious order, one circuit is loaded too heavily. Move the plugs around so no circuit is overloaded, and then make the three as even as you can. Moving a server never changes the total power — only which circuit carries it."
    },
    "lever": {
     "standard": "It is a bin-packing problem with three bins and a per-bin continuous-load ceiling; the imbalance objective breaks ties between packings that all pass.",
     "novice": "Think of three buckets that must not overflow. Several arrangements pass; the best one is the most even."
    },
    "how": {
     "standard": "Open the Labs tab in the app, pick this lab, read its goal and constraints, and build the scenario with the controls this module already used. Run and grade replays the same pure engine and scores the trace: every constraint is measured from the trace, not taken on trust, so an idle build cannot pass. Thresholds and scores are illustrative.",
     "novice": "In the app, open the tab called Labs and choose this lab. It states a goal and some rules. Set the controls the way you think will work, then press Run and grade. The app checks what actually happened in the run, so you cannot pass by doing nothing. Change one setting at a time and grade again. The pass marks are made up for teaching, not measurements."
    },
    "cite": [
     "PhysicsRackPower/backend/tests/test_labs.py::test_lab_invariants",
     "PhysicsRackPower/backend/tests/test_labs.py::test_there_are_three_labs_of_rising_difficulty"
    ]
   },
   "bridge": {
    "text": {
     "standard": "Return to the course home to pick another module.",
     "novice": "Go back to the course home to choose what to do next."
    },
    "next": null
   }
  },
  {
   "id": "E2",
   "title": "Shared chassis: the noisy neighbor",
   "core": false,
   "idea": {
    "standard": "One hot sled taxes the chassis fans for all eight bays.",
    "novice": "In a chassis where eight servers share the fans, one busy server makes the fans work harder for everyone."
   },
   "prereqs": [],
   "background": {
    "standard": "The MX7000 is a 7U chassis with eight bays. A sled is a server that slides into one bay; the nine fans and the pooled power supplies (PSUs) belong to the chassis, not to any sled. N+1 redundancy means one spare PSU. Grid redundancy splits the PSUs across two separate AC feeds from the building, so it also covers a whole feed failing.",
    "novice": "This is one large box with eight slots. Each slot holds a slide-in server, called a sled. The box's nine fans and its power supplies are shared: they belong to the box, not to any one server. There are two ways to arrange spare power supplies. One keeps a single spare, which covers a power supply dying. The other splits them across two separate cables from the building, which also covers one of those cables dying."
   },
   "objectives": [],
   "entries": [
    {
     "twin": "PhysicsMX7000",
     "port": 5212,
     "pageTitle": "MX7000 Shared-Infrastructure Simulator",
     "name": "MX7000 modular chassis physics",
     "links": [
      {
       "kind": "scenario",
       "id": "noisy-neighbor",
       "title": "The noisy neighbor, thermally",
       "label": "The noisy neighbor, thermally",
       "how": {
        "standard": "The busy sled only starts two minutes into the run, so use a faster speed to reach t=120 s. Read the per-sled power list and the fan line in Instruments before and after.",
        "novice": "Nothing happens for the first two minutes of the run, so press a faster speed. Then compare the list of eight servers' watts, and the fan line, before and after one of them gets busy."
       }
      }
     ]
    }
   ],
   "predict": {
    "q": {
     "standard": "One sled runs at 100% and seven sit idle. Do the seven idle sleds draw more power than before?",
     "novice": "One of eight servers works hard and the rest do nothing. Do the idle ones start using more power?"
    },
    "options": [
     "Yes, a little each",
     "No, but the shared fan bill rises",
     "No, and nothing else changes"
    ],
    "answer": 1,
    "reveal": {
     "standard": "No. The seven draw what they drew before, within 2 W, but the shared fan wall spins up by more than 10 points and the fan power rises by more than 15 W for everyone.",
     "novice": "No, the idle servers are unchanged. But the shared fans spin up for the busy one, and everyone pays for that."
    },
    "cite": [
     "PhysicsMX7000/backend/tests/test_engine.py::test_noisy_neighbor_taxes_the_shared_fans"
    ]
   },
   "checks": [
    {
     "q": {
      "standard": "Which slot does the fan controller target?",
      "novice": "The fans speed up for one of the eight servers. Which one?"
     },
     "a": {
      "standard": "The hottest one: slot 1, the noisy sled. The readout names it.",
      "novice": "The hottest one, which here is the busy server in slot 1. The fans follow whichever server is hottest, whatever the other seven are doing."
     },
     "cite": [
      "PhysicsMX7000/backend/tests/test_engine.py::test_noisy_neighbor_taxes_the_shared_fans"
     ]
    },
    {
     "q": {
      "standard": "With N+1 PSU redundancy, does the chassis survive losing a whole AC feed?",
      "novice": "With just one spare power supply, does the box keep running when a whole supply cable from the building fails?"
     },
     "a": {
      "standard": "No. N+1 covers one supply dying, not a feed dying, which takes down every PSU on that feed at once. Grid redundancy rides through the same event, because the surviving feed still carries half the supplies.",
      "novice": "No. One spare covers one power supply failing. A whole cable failing takes out several supplies at the same time. The other arrangement, split across two cables, survives it."
     },
     "cite": [
      "PhysicsMX7000/backend/tests/test_engine.py::test_nplus1_does_not_survive_a_feed_loss",
      "PhysicsMX7000/backend/tests/test_engine.py::test_grid_redundancy_survives_a_whole_feed_loss"
     ]
    }
   ],
   "pins": [],
   "lab": {
    "twin": "PhysicsMX7000",
    "port": 5212,
    "id": "spread-the-heat",
    "title": "Spread the heat",
    "difficulty": 1,
    "label": "Open the lab: Spread the heat",
    "goal": {
     "standard": "Four sleds flat out and four idle is tidy, and the shared fan wall pays for it. Deliver the same work with the chassis fans averaging far less, then get mean wall power down. The fan controller tracks the hottest sled, so concentration is the thing being priced.",
     "novice": "Half the blades work hard and half do nothing. That looks neat, but the fans — which are shared by everything — run fast because of the hottest blade. Do the same amount of work with the fans running much slower, and use less electricity at the wall."
    },
    "lever": {
     "standard": "Spread the same total load over more sleds: the hottest-sled target falls, and fan power goes with speed cubed.",
     "novice": "Share the work out over all the blades. No blade gets as hot, so the fans can run slower — and slower fans cost much less."
    },
    "how": {
     "standard": "Open the Labs tab in the app, pick this lab, read its goal and constraints, and build the scenario with the controls this module already used. Run and grade replays the same pure engine and scores the trace: every constraint is measured from the trace, not taken on trust, so an idle build cannot pass. Thresholds and scores are illustrative.",
     "novice": "In the app, open the tab called Labs and choose this lab. It states a goal and some rules. Set the controls the way you think will work, then press Run and grade. The app checks what actually happened in the run, so you cannot pass by doing nothing. Change one setting at a time and grade again. The pass marks are made up for teaching, not measurements."
    },
    "cite": [
     "PhysicsMX7000/backend/tests/test_labs.py::test_lab_invariants",
     "PhysicsMX7000/backend/tests/test_labs.py::test_there_are_three_labs_of_rising_difficulty"
    ]
   },
   "bridge": {
    "text": {
     "standard": "Return to the course home to pick another module.",
     "novice": "Go back to the course home to choose what to do next."
    },
    "next": null
   }
  },
  {
   "id": "E3",
   "title": "Rugged edge: the filter nobody changed",
   "core": false,
   "idea": {
    "standard": "A fouled filter turns a heat wave the server could survive into one it throttles through.",
    "novice": "A dusty air filter can be the difference between a server coping with a hot day and a server slowing down."
   },
   "prereqs": [],
   "background": {
    "standard": "The XR servers are short, rugged PowerEdges built to live outside a data hall, with a dust filter ahead of the drives. Airflow is measured in CFM (cubic feet per minute); throttling is the server slowing its processors and accelerators to stay under a temperature limit. The build in this run carries accelerators — add-in cards at 75 W each — and the instruments report the work they lose while throttled.",
    "novice": "These servers are built to sit outside a proper computer room, bolted to a factory wall or a cabinet at a phone mast, so their air comes in through a dust filter. Airflow is measured in CFM. Throttling means the server deliberately slows itself down to keep its temperature safe. The machine in this run also carries add-in cards for extra number-crunching, called accelerators, and the screen shows how much of their work is lost when it slows down."
   },
   "objectives": [],
   "entries": [
    {
     "twin": "PhysicsXR",
     "port": 5213,
     "pageTitle": "PowerEdge XR Rugged-Edge Physics Simulator",
     "name": "PowerEdge XR rugged edge physics",
     "links": [
      {
       "kind": "scenario",
       "id": "filter-nobody-changed",
       "title": "The filter nobody changed",
       "label": "The filter nobody changed",
       "how": {
        "standard": "Use a faster speed to get through the heat wave. Below the map, Months since filter service sets the filter's state at t=0, and the Change the filter now button cleans it mid-run — that button is what the second question below asks about. To run the clean-filter comparison instead, set the slider to 0 and press Restart run.",
        "novice": "Press a faster speed to get through the hot day. Under the picture, a slider sets how long the filter has gone unserviced, and a button called Change the filter now cleans it while the run is playing — that button is what the second question asks about. To compare against a clean filter from the start, set the slider to 0 and press Restart run."
       }
      }
     ]
    }
   ],
   "predict": {
    "q": {
     "standard": "Same build, same heat wave. One filter has six months of heavy dust, the other is new. Which one throttles?",
     "novice": "Two identical servers on a very hot day. One has a clogged dust filter, one has a clean filter. Which one slows down?"
    },
    "options": [
     "Both",
     "Only the fouled one",
     "Neither"
    ],
    "answer": 1,
    "reveal": {
     "standard": "Only the fouled one. The clean filter rides out the same day with zero throttle seconds, and the fouled filter visibly costs airflow for the same fan wall.",
     "novice": "Only the dusty one. Clean air filters let enough air through; the clogged one does not."
    },
    "cite": [
     "PhysicsXR/backend/tests/test_engine.py::test_fouled_filter_throttles_where_a_clean_one_survives"
    ]
   },
   "checks": [
    {
     "q": {
      "standard": "At constant work, what does fouling cost?",
      "novice": "If the server keeps doing the same work, what does a dusty filter cost?"
     },
     "a": {
      "standard": "Fan power. The fans spin faster to push the same air through a dirtier filter, while CPU power is unchanged.",
      "novice": "Electricity for the fans. They have to work harder to pull the same amount of air through the dirty filter. The processor's own power does not change at all."
     },
     "cite": [
      "PhysicsXR/backend/tests/test_engine.py::test_fouling_costs_fan_power_at_constant_work"
     ]
    },
    {
     "q": {
      "standard": "What happens right after a clean-filter event — the Change the filter now button, pressed mid-run?",
      "novice": "What happens right after you press Change the filter now in the middle of a run?"
     },
     "a": {
      "standard": "Fouling drops to 0 and the fans relax: the same rpm now moves more air, so the controller backs the fan wall down.",
      "novice": "The filter is clean again, so the same fan speed moves more air, and the fans slow down straight away."
     },
     "cite": [
      "PhysicsXR/backend/tests/test_engine.py::test_clean_filter_event_restores_airflow"
     ]
    }
   ],
   "pins": [],
   "lab": {
    "twin": "PhysicsXR",
    "port": 5213,
    "id": "dust-and-heat",
    "title": "Six months of dust, one hot afternoon",
    "difficulty": 1,
    "label": "Open the lab: Six months of dust, one hot afternoon",
    "goal": {
     "standard": "A fouled filter, a hot afternoon, and nobody able to reach the site. Deliver the work for the whole run without a second of throttling. The lesson is where the throttle lands: the accelerators are in their own air lane, so turning the CPU down buys nothing.",
     "novice": "The air filter has not been changed for months, the afternoon is hot, and nobody can visit. Keep the work going for the whole run without the machine ever slowing itself down. The trick is knowing which part is actually overheating."
    },
    "lever": {
     "standard": "Fouling is an airflow-resistance penalty: the same rpm moves less air, and the controller buys it back at the cubic price. Ease the dial on the lane that is actually hot.",
     "novice": "A dirty filter means the fans move less air at the same speed. Find which part is too hot and ease off that one, not the others."
    },
    "how": {
     "standard": "Open the Labs tab in the app, pick this lab, read its goal and constraints, and build the scenario with the controls this module already used. Run and grade replays the same pure engine and scores the trace: every constraint is measured from the trace, not taken on trust, so an idle build cannot pass. Thresholds and scores are illustrative.",
     "novice": "In the app, open the tab called Labs and choose this lab. It states a goal and some rules. Set the controls the way you think will work, then press Run and grade. The app checks what actually happened in the run, so you cannot pass by doing nothing. Change one setting at a time and grade again. The pass marks are made up for teaching, not measurements."
    },
    "cite": [
     "PhysicsXR/backend/tests/test_labs.py::test_lab_invariants",
     "PhysicsXR/backend/tests/test_labs.py::test_there_are_three_labs_of_rising_difficulty"
    ]
   },
   "bridge": {
    "text": {
     "standard": "Return to the course home to pick another module.",
     "novice": "Go back to the course home to choose what to do next."
    },
    "next": null
   }
  },
  {
   "id": "E4",
   "title": "Dedupe as arithmetic: the entropy alarm",
   "core": false,
   "idea": {
    "standard": "The entropy of today's changed data raises the alarm within days; capacity notices weeks later.",
    "novice": "Encrypted data looks like random noise. Watching for that noise in each day's backup catches ransomware long before the disks fill up."
   },
   "prereqs": [],
   "background": {
    "standard": "A backup appliance stores each day's backup once, by recognising the pieces it already holds — deduplication. Entropy here means how random the day's changed data looks, and encrypted data looks random. The dedupe ratio is logical data over physical data stored: an outcome, never a setting.",
    "novice": "A backup machine saves space by noticing which parts of today's backup it already has, and keeping only what is new. That is called deduplication. Encryption scrambles data so it looks like random noise, and the simulator measures how random-looking each day's new data is. The ratio on screen is how much data the customer thinks is stored, divided by how much disk it really takes."
   },
   "objectives": [],
   "entries": [
    {
     "twin": "PhysicsDataDomain",
     "port": 5215,
     "pageTitle": "Data Domain Dedupe Physics",
     "name": "Data Domain dedupe physics",
     "links": [
      {
       "kind": "scenario",
       "id": "entropy-alarm",
       "title": "Entropy as a smoke alarm",
       "label": "Entropy as a smoke alarm",
       "lockedLabel": "The run where ransomware starts on day 40",
       "how": {
        "standard": "The run is 90 days at a day a tick; use a faster speed. Watch two readouts as day 40 passes: the entropy of the day's changed data, and the capacity curve. The figures are the simulator's estimates.",
        "novice": "The run covers 90 days, so press a faster speed. As day 40 goes by, watch two things: how random the new data looks, and how fast the disks are filling. The numbers are the simulator's estimates."
       }
      }
     ]
    }
   ],
   "predict": {
    "q": {
     "standard": "Ransomware starts on day 40. Which notices first: the entropy of the changed data, or the capacity curve?",
     "novice": "An attack starts on day 40. Which spots it first: checking how random each day's new data looks, or watching the disks fill?"
    },
    "options": [
     {
      "standard": "Entropy, within days",
      "novice": "The randomness check, within days"
     },
     {
      "standard": "Capacity, within days",
      "novice": "The disks filling up, within days"
     },
     "Both on the same day"
    ],
    "answer": 0,
    "reveal": {
     "standard": "Entropy. The alarm fires between day 40 and day 42; the capacity curve leaves its trend weeks later.",
     "novice": "The randomness check, within two days. The disk graph takes weeks to look wrong."
    },
    "cite": [
     "PhysicsDataDomain/backend/tests/test_engine.py::test_acceptance_entropy_alarm_fires_before_capacity_notices"
    ]
   },
   "checks": [
    {
     "q": {
      "standard": "Data that is already high-entropy but static: does it dedupe?",
      "novice": "Data that already looks random but never changes — does the machine still save space on it?"
     },
     "a": {
      "standard": "Yes. The same pieces arrive every day, so they are stored once; what random-looking data will not do is compress.",
      "novice": "Yes. The same pieces come back every day, so it only keeps them once. What it cannot do is squeeze them any smaller."
     },
     "cite": [
      "PhysicsDataDomain/backend/tests/test_engine.py::test_static_high_entropy_still_dedupes_but_does_not_compress"
     ]
    },
    {
     "q": {
      "standard": "Is the dedupe ratio a setting?",
      "novice": "Can you set the space-saving ratio?"
     },
     "a": {
      "standard": "No. It is the quotient of logical over physical, and physical is a ledger that must balance every day: yesterday's total, plus what was new, minus what expired.",
      "novice": "No. It is the result of a sum, not a dial. The disk used today is yesterday's disk, plus whatever was new, minus whatever aged out."
     },
     "cite": [
      "PhysicsDataDomain/backend/tests/test_engine.py::test_capacity_conservation_every_day"
     ]
    }
   ],
   "pins": [],
   "lab": {
    "twin": "PhysicsDataDomain",
    "port": 5215,
    "id": "branch-box-memory",
    "title": "How long can the branch box remember?",
    "difficulty": 1,
    "label": "Open the lab: How long can the branch box remember?",
    "goal": {
     "standard": "Retention is the ratio's engine, so turn it up — on the entry appliance, protecting a dataset with a modest daily change rate. Get the highest dedupe ratio you can while the store stays under its fill line and the fingerprint index never outgrows its RAM.",
     "novice": "The longer you keep backups, the better deduplication looks, because each new backup is mostly a copy of yesterday's. So keep as much history as you can — without filling the appliance up, and without the index of what it has seen outgrowing its memory."
    },
    "lever": {
     "standard": "Physical growth per generation is the novel fraction, so retention buys ratio linearly until either the capacity line or the index RAM binds. Find which binds first.",
     "novice": "Each extra day of history costs only the part that changed. Push it until either the disk or the memory runs out — then stop just before."
    },
    "how": {
     "standard": "Open the Labs tab in the app, pick this lab, read its goal and constraints, and build the scenario with the controls this module already used. Run and grade replays the same pure engine and scores the trace: every constraint is measured from the trace, not taken on trust, so an idle build cannot pass. Thresholds and scores are illustrative.",
     "novice": "In the app, open the tab called Labs and choose this lab. It states a goal and some rules. Set the controls the way you think will work, then press Run and grade. The app checks what actually happened in the run, so you cannot pass by doing nothing. Change one setting at a time and grade again. The pass marks are made up for teaching, not measurements."
    },
    "cite": [
     "PhysicsDataDomain/backend/tests/test_labs.py::test_lab_invariants",
     "PhysicsDataDomain/backend/tests/test_labs.py::test_there_are_three_labs_of_rising_difficulty"
    ]
   },
   "bridge": {
    "text": {
     "standard": "Return to the course home to pick another module.",
     "novice": "Go back to the course home to choose what to do next."
    },
    "next": null
   }
  },
  {
   "id": "E5",
   "title": "Modernize without migrating",
   "core": false,
   "idea": {
    "standard": "A new generation joins a live cluster with zero downtime; the 3× only arrives after cutover.",
    "novice": "New storage hardware joins the old while everything keeps running, and the speed-up only shows once the switch-over is done."
   },
   "prereqs": [],
   "background": {
    "standard": "The trace is a new-generation appliance joining a live cluster beside the previous one. IOPS is I/O operations per second, the storage speed counter. The rebalance is the cluster moving data onto the new appliance while hosts keep reading and writing; cutover is the moment the new hardware takes over the serving. Effective capacity is what the cluster offers after data reduction.",
    "novice": "A new storage box joins the old one while everything keeps running. The speed counter is in IOPS: reads and writes per second. First the cluster copies data across in the background, which is called the rebalance. Then the new box takes over the serving, which is called the cutover — the module uses that one word for that moment throughout. Capacity is quoted as effective capacity, meaning after the array has squeezed the data down."
   },
   "objectives": [],
   "entries": [
    {
     "twin": "DellPowerStoreElite",
     "port": 5220,
     "pageTitle": "PowerStore Elite Inside",
     "trace": "join",
     "name": "PowerStore Elite cluster join",
     "links": [
      {
       "kind": "tour",
       "id": "zero-downtime-join",
       "label": "Guided tour, at the zero-downtime join",
       "lockedLabel": "Guided tour, at the join"
      },
      {
       "kind": "phase",
       "value": "rebalance",
       "label": "Join trace, at the live rebalance"
      }
     ]
    }
   ],
   "predict": {
    "q": {
     "standard": "During the longest stage of the join, the live rebalance, how many seconds of downtime do hosts see?",
     "novice": "While the new hardware takes over the data, how long are the applications cut off?"
    },
    "options": [
     "None",
     {
      "standard": "A few seconds per volume",
      "novice": "A few seconds, each time a piece of data moves"
     },
     {
      "standard": "Minutes, during cutover",
      "novice": "Minutes, while the new box takes over"
     }
    ],
    "answer": 0,
    "reveal": {
     "standard": "None, on every step: the downtime counter reads 0 s throughout. The rebalance may tax service, never stop it — the IOPS counter dips from 250K to 230K and comes back, and the twin's test pins it above 85% of baseline. The figures are illustrative.",
     "novice": "Not at all: the downtime counter stays at 0 seconds. Things run a little slower during the move — the speed counter dips from 250K to 230K — but they never stop. The numbers are illustrative."
    },
    "cite": [
     "DellPowerStoreElite/backend/tests/test_engine.py::test_downtime_is_always_zero",
     "DellPowerStoreElite/backend/tests/test_engine.py::test_service_never_pauses"
    ]
   },
   "checks": [
    {
     "q": {
      "standard": "When does the cluster serve at least 3× its baseline?",
      "novice": "When does the storage actually get about three times faster?"
     },
     "a": {
      "standard": "Only from cutover on: the IOPS counter reads 250K before it and 760K at cutover, having stayed at or below 1.2× baseline throughout the join and rebalance. The tripling is Dell's claim for this appliance; the twin's figures are illustrative.",
      "novice": "Only once the switch has happened. The speed counter reads 250K through the whole copy, then 760K at the cutover. Tripling the speed is Dell's own claim for this product, and the simulator's numbers are illustrative."
     },
     "cite": [
      "DellPowerStoreElite/backend/tests/test_engine.py::test_performance_triples_only_after_cutover"
     ]
    },
    {
     "q": {
      "standard": "When does effective capacity jump?",
      "novice": "When does the amount of space the cluster offers go up?"
     },
     "a": {
      "standard": "Exactly once, at the join: the panel reads 1.2 PB before it and 7.0 PB after, and never moves again. Dell's effective-capacity figures assume its data-reduction guarantee; the twin's numbers are illustrative.",
      "novice": "Once, the moment the new box joins: the panel goes from 1.2 PB to 7.0 PB and then stays there. Those capacity figures assume Dell's promise about how far it can squeeze data, and the simulator's numbers are illustrative."
     },
     "cite": [
      "DellPowerStoreElite/backend/tests/test_engine.py::test_effective_capacity_only_grows_and_jumps_at_the_join"
     ]
    }
   ],
   "pins": [],
   "bridge": {
    "text": {
     "standard": "Return to the course home to pick another module.",
     "novice": "Go back to the course home to choose what to do next."
    },
    "next": null
   }
  },
  {
   "id": "E6",
   "title": "The laptop's power path",
   "core": false,
   "idea": {
    "standard": "An unrecognized adapter throttles the laptop, but the power-up sequence still completes.",
    "novice": "If the laptop doesn't recognize its charger, it slows itself down and stops charging, but it still starts up."
   },
   "prereqs": [],
   "background": {
    "standard": "The adapter and the laptop exchange an identity signal down a third conductor in the barrel plug — Dell calls it the PSID, the power supply ID. If the laptop cannot read it, it does not know how many watts are safe to draw, so it caps the CPU and GPU and refuses to charge. Steady state is the end of the trace, where the load has settled.",
    "novice": "The charger and the laptop talk to each other through an extra wire in the plug, so the laptop knows how powerful the charger is. If it cannot read that, it has no idea how much power it is safe to take, so it limits its processor and graphics chip and will not charge the battery. The end of the run, where everything has settled, is called steady state."
   },
   "objectives": [],
   "entries": [
    {
     "twin": "DellAlienware",
     "port": 5176,
     "pageTitle": "Alienware m18 Digital Twin",
     "name": "Alienware power path",
     "links": [
      {
       "kind": "tour",
       "id": "psid-handshake",
       "label": "Guided tour, at the charger handshake"
      },
      {
       "kind": "phase",
       "value": "handshake",
       "label": "Power trace, at the handshake"
      }
     ]
    }
   ],
   "predict": {
    "q": {
     "standard": "The adapter fails the 1-Wire PSID handshake. Does the laptop still reach steady state?",
     "novice": "The laptop can't confirm its charger is genuine. Does it still finish starting up?"
    },
    "options": [
     {
      "standard": "Yes, throttled and not charging",
      "novice": "Yes, but slowed down, and it will not charge"
     },
     {
      "standard": "No, it refuses to boot",
      "novice": "No, it refuses to start at all"
     },
     "Yes, at full speed"
    ],
    "answer": 0,
    "reveal": {
     "standard": "Yes. On the last step the instruments read CPU 15 W, GPU 10 W, system 50 W, charge 0 W, regime \"throttled (adapter not recognized)\" — the phase machine still ends at steady. The twin's test pins the same run: charging off throughout and CPU plus GPU never above 40 W. Figures are illustrative.",
     "novice": "Yes. At the end the screen reads 15 W for the processor and 10 W for the graphics — a fraction of what they can draw — charging 0 W, and a note that the charger was not recognised. It won't charge and it runs slowly, but it still starts up. The figures are illustrative."
    },
    "cite": [
     "DellAlienware/backend/tests/test_engine.py::test_unrecognized_adapter_is_throttled"
    ]
   },
   "checks": [
    {
     "q": {
      "standard": "Does the battery level rise with an unrecognized adapter?",
      "novice": "With a charger the laptop cannot identify, does the battery fill up?"
     },
     "a": {
      "standard": "No. Charge power is 0 in every phase, so the battery counter ends exactly where it started.",
      "novice": "No. Charging is switched off the whole way through, so the battery percentage never moves from where it began."
     },
     "cite": [
      "DellAlienware/backend/tests/test_engine.py::test_unrecognized_adapter_is_throttled"
     ]
    },
    {
     "q": {
      "standard": "Starting deeply discharged, in what order does charging go?",
      "novice": "Starting from nearly empty, what order do the charging stages come in?"
     },
     "a": {
      "standard": "Precharge, then constant current, then constant voltage.",
      "novice": "First a gentle trickle to wake the cells, called precharge. Then the fast part, at a steady current. Then a slow finish, at a steady voltage."
     },
     "cite": [
      "DellAlienware/backend/tests/test_engine.py::test_charge_ramp_stages_in_order"
     ]
    }
   ],
   "pins": [],
   "lab": {
    "twin": "DellAlienware",
    "port": 5176,
    "id": "fit-the-brick",
    "title": "Fit the game inside the brick",
    "difficulty": 1,
    "label": "Open the lab: Fit the game inside the brick",
    "goal": {
     "standard": "At full tilt the machine asks for more than the adapter can give, and the pack drains while plugged in. Find the fastest setup that stays inside the adapter with the pack still charging at steady state — the hybrid-power column of this module's energy identity, closed.",
     "novice": "Playing at the highest setting asks the laptop for more power than the charger can supply, so the battery quietly drains even though it is plugged in. Find the fastest settings that the charger can actually keep up with, with the battery still filling."
    },
    "lever": {
     "standard": "Thermal mode and the load dials set demand; the adapter rating is the ceiling; whatever is left after the system is what charges.",
     "novice": "Turn the performance mode down step by step until the charger can cover the machine and still have something left for the battery."
    },
    "how": {
     "standard": "Open the Labs tab in the app, pick this lab, read its goal and constraints, and build the scenario with the controls this module already used. Run and grade replays the same pure engine and scores the trace: every constraint is measured from the trace, not taken on trust, so an idle build cannot pass. Thresholds and scores are illustrative.",
     "novice": "In the app, open the tab called Labs and choose this lab. It states a goal and some rules. Set the controls the way you think will work, then press Run and grade. The app checks what actually happened in the run, so you cannot pass by doing nothing. Change one setting at a time and grade again. The pass marks are made up for teaching, not measurements."
    },
    "cite": [
     "DellAlienware/backend/tests/test_labs.py::test_lab_invariants",
     "DellAlienware/backend/tests/test_labs.py::test_there_are_three_labs_of_rising_difficulty"
    ]
   },
   "bridge": {
    "text": {
     "standard": "Return to the course home to pick another module.",
     "novice": "Go back to the course home to choose what to do next."
    },
    "next": null
   },
   "failures": [
    {
     "twin": "DellAlienware",
     "port": 5176,
     "name": "Alienware: plugged in, not charging",
     "scenario": "charge-taper-diagnostics",
     "at": {
      "kind": "phase",
      "value": "heat"
     },
     "request": {
      "method": "POST",
      "endpoint": "simulate",
      "body": {
       "scenario": {
        "profileId": "m18-r2",
        "adapterId": "barrel-280",
        "startBatteryPct": 20,
        "thermalMode": "balanced",
        "workload": "gaming"
       }
      }
     },
     "label": "Charging-diagnostics trace, paused on the hot pack",
     "lockedLabel": "Charging-diagnostics trace, paused where it says Not charging",
     "q": {
      "standard": "The game has just been closed. The laptop is on its genuine 280 W adapter, the BIOS AC Adapter line reads 280 W, the system draws about 60 W, and the battery sits at 89%, but the status says Not charging. Is the adapter at fault, and what will make charging start again?",
      "novice": "You have just stopped playing a game. The laptop is plugged into its proper charger, the battery is at 89%, and it says Not charging. Is the charger broken? What will get it charging again?"
     },
     "options": [
      {
       "standard": "The adapter failed its handshake; replace it",
       "novice": "The charger could not identify itself; replace the charger"
      },
      {
       "standard": "The pack is too hot; airflow and time, then it resumes unprompted",
       "novice": "The battery is too hot; give it air and time, and it starts again on its own"
      },
      {
       "standard": "The 80% charge cap is active; change the BIOS charge mode",
       "novice": "A setting is holding it at 80%; change that setting"
      }
     ],
     "answer": 1,
     "a": {
      "standard": "The adapter is fine: the BIOS line reads its full wattage and about 220 W of headroom is unused. The pack is over its charge-temperature limit (46.5 °C here), so the charger holds charge power at zero to protect cycle life. The 45 °C trip is illustrative: it is the cell-level lithium-ion charge window, and Dell does not publish the firmware threshold. The status line reads the same Not charging it showed at the 80% cap; the pack temperature tells the cases apart. Replugging does nothing. The next state shows the pack back under the trip at 43.8 °C and still not charging, because the charger re-arms with hysteresis at an illustrative 42 °C. Charging then resumes unprompted and rejoins the taper at a lower wattage than before the pause. The only state in the walk that needs a part is the later swap phase, where the AC Adapter line reads Unknown.",
      "novice": "The charger is fine; the laptop recognises it at its full 280 W. The battery is simply too hot to charge safely after the game, so the laptop waits. The message looks the same as when charging stops at an 80% limit; the battery temperature is what tells you which case you are in. Unplugging and replugging does nothing. Let it cool with some airflow and it starts charging again by itself, a little after it drops below the limit, and more slowly than before because the battery is nearly full. The temperature figures are illustrative; Dell does not publish the exact ones."
     },
     "cite": [
      "DellAlienware/backend/tests/test_diagnostics.py::test_the_heat_pause_is_not_a_budget_problem",
      "DellAlienware/backend/tests/test_diagnostics.py::test_no_charge_while_the_pack_is_over_its_temperature_limit",
      "DellAlienware/backend/tests/test_diagnostics.py::test_charge_resumes_unprompted_only_after_the_pack_cools",
      "DellAlienware/backend/tests/test_diagnostics.py::test_the_thermal_inhibit_holds_until_the_resume_temperature",
      "DellAlienware/backend/tests/test_diagnostics.py::test_the_status_line_does_not_name_the_cause"
     ],
     "pins": [
      {
       "step": 12,
       "field": "packTempC",
       "value": 46.5
      },
      {
       "step": 12,
       "field": "chargeW",
       "value": 0.0
      },
      {
       "step": 12,
       "field": "systemW",
       "value": 60.0
      },
      {
       "step": 12,
       "field": "adapterReadout",
       "value": "280 W"
      },
      {
       "step": 13,
       "field": "packTempC",
       "value": 43.8
      },
      {
       "step": 13,
       "field": "chargeW",
       "value": 0.0
      },
      {
       "step": 16,
       "field": "adapterReadout",
       "value": "Unknown"
      }
     ]
    }
   ]
  },
  {
   "id": "E7",
   "title": "The data pipeline: the bottleneck moves",
   "core": false,
   "idea": {
    "standard": "Throughput is the minimum of the stages, so fixing one stage moves the bottleneck somewhere else.",
    "novice": "A pipeline runs only as fast as its slowest step. Speed up that step and a different step becomes the slowest."
   },
   "prereqs": [],
   "background": {
    "standard": "The pipeline is a chain of stages: data arrives, is cleaned, is indexed, and is served to the GPUs. Throughput is the minimum of the stages' rates, so one stage is the constraint and the rest carry slack. Backlog is the queue in front of the constraint, and the GPU idle due to data gauge is the share of GPU time spent waiting for data to show up.",
    "novice": "Data goes through a chain of steps: it arrives, it is cleaned up, it is filed, and then it is handed to the expensive computers. The chain moves only as fast as its slowest step, so work piles up in front of that step. One gauge on screen shows how much of the expensive computers' time is spent waiting for data."
   },
   "objectives": [],
   "entries": [
    {
     "twin": "PhysicsData",
     "port": 5210,
     "pageTitle": "Data &amp; Observability &middot; Pipeline Simulator",
     "name": "Data pipeline physics",
     "links": [
      {
       "kind": "scenario",
       "id": "find-the-bottleneck",
       "title": "Find the bottleneck",
       "label": "Find the bottleneck",
       "how": {
        "standard": "The run is 360 hours at an hour a tick and turns GPU processing on for you at hour 120, so use a faster speed. Watch the \"limited by\" readout: process, then index while the backlog drains, then arrival. The GPUs are served the pipeline's throughput plus about 5 TB/h of re-reads, which is why the idle gauge reads 0 while the backlog is draining. Rates are illustrative.",
        "novice": "The run covers 360 hours, an hour per tick, and at hour 120 it speeds up the cleaning step for you — press a faster speed to get there. Watch the line that says what is holding the pipeline back: first the cleaning step, then the next one, and at the end the data simply arriving. The rates are illustrative."
       }
      }
     ]
    }
   ],
   "predict": {
    "q": {
     "standard": "Processing is the bottleneck. Turn on GPU processing. Where is the bottleneck now?",
     "novice": "The slowest step is processing. You make processing much faster. What is the slowest step now?"
    },
    "options": [
     "Still processing",
     "Somewhere else",
     "Nowhere; the pipeline is balanced"
    ],
    "answer": 1,
    "reveal": {
     "standard": "Somewhere else. The constraint relocates and throughput does not fall.",
     "novice": "A different step. Fixing one slow part just shows you the next one."
    },
    "cite": [
     "PhysicsData/backend/tests/test_engine.py::test_fixing_the_bottleneck_moves_it"
    ]
   },
   "checks": [
    {
     "q": {
      "standard": "If arrival stays above the constraint, what grows?",
      "novice": "If data keeps arriving faster than the slowest step can handle, what grows?"
     },
     "a": {
      "standard": "The backlog at the constraint, and the freshness lag with it: days-old data being served, and no error message anywhere.",
      "novice": "The queue in front of that step, and how old the data being served is. Nothing shows an error; the answers just quietly get staler."
     },
     "cite": [
      "PhysicsData/backend/tests/test_engine.py::test_backlog_and_freshness_grow_when_arrival_exceeds_the_constraint"
     ]
    },
    {
     "q": {
      "standard": "What does a serving shortfall show up as?",
      "novice": "If the chain cannot feed the expensive computers as fast as they want, where do you see that?"
     },
     "a": {
      "standard": "As the GPU idle due to data gauge: it opens near 31% in this run, and the twin's test pins a shortfall above 20%. Rates are illustrative.",
      "novice": "On the gauge for the expensive computers waiting: it opens near 31% in this run, then falls once the slow step is fixed. The rates are illustrative."
     },
     "cite": [
      "PhysicsData/backend/tests/test_engine.py::test_gpu_idle_reflects_serving_shortfall"
     ]
    }
   ],
   "pins": [],
   "lab": {
    "twin": "PhysicsData",
    "port": 5210,
    "id": "quiet-and-quick",
    "title": "A detector that is quiet and quick",
    "difficulty": 1,
    "label": "Open the lab: A detector that is quiet and quick",
    "goal": {
     "standard": "Issues are planted at known hours. Tune the detector so most of its flags are real, every planted issue is found, and mean time to detect stays inside the budget — then make detection as fast as the precision floor allows. Grading is against planted ground truth, not against the detector's own opinion.",
     "novice": "Problems have been hidden in the data at times the app knows. Tune the alarm so that most alarms are genuine, none of the hidden problems is missed, and the alarms arrive quickly. Then make it as quick as it can be without becoming noisy."
    },
    "lever": {
     "standard": "Sensitivity trades precision against detection latency along one curve; the recall floor forbids the quiet end and the precision floor forbids the loud end.",
     "novice": "One dial makes the alarm more eager: it finds things sooner but cries wolf more often. The rules block both extremes, so find the middle."
    },
    "how": {
     "standard": "Open the Labs tab in the app, pick this lab, read its goal and constraints, and build the scenario with the controls this module already used. Run and grade replays the same pure engine and scores the trace: every constraint is measured from the trace, not taken on trust, so an idle build cannot pass. Thresholds and scores are illustrative.",
     "novice": "In the app, open the tab called Labs and choose this lab. It states a goal and some rules. Set the controls the way you think will work, then press Run and grade. The app checks what actually happened in the run, so you cannot pass by doing nothing. Change one setting at a time and grade again. The pass marks are made up for teaching, not measurements."
    },
    "cite": [
     "PhysicsData/backend/tests/test_labs.py::test_lab_invariants",
     "PhysicsData/backend/tests/test_labs.py::test_there_are_three_labs_of_rising_difficulty"
    ]
   },
   "bridge": {
    "text": {
     "standard": "Return to the course home to pick another module.",
     "novice": "Go back to the course home to choose what to do next."
    },
    "next": null
   }
  }
 ],
 "tracks": [
  {
   "id": "full",
   "title": "The whole course",
   "for": "Anyone, in order",
   "time": "6 to 8 hours",
   "steps": [
    {
     "module": "M1"
    },
    {
     "module": "M2"
    },
    {
     "module": "M3"
    },
    {
     "module": "M4"
    },
    {
     "module": "M5"
    },
    {
     "module": "M6"
    },
    {
     "module": "M7"
    },
    {
     "module": "M8"
    },
    {
     "module": "M9"
    },
    {
     "module": "M10"
    },
    {
     "module": "M11"
    },
    {
     "module": "M12"
    }
   ]
  },
  {
   "id": "ai-infrastructure",
   "title": "AI infrastructure",
   "for": "Architects building GPU clusters",
   "time": "3 hours",
   "steps": [
    {
     "module": "M1"
    },
    {
     "module": "M4"
    },
    {
     "module": "M5"
    },
    {
     "module": "M7",
     "only": [
      "DellExascale"
     ]
    },
    {
     "module": "M8"
    },
    {
     "module": "M12"
    }
   ]
  },
  {
   "id": "storage-admin",
   "title": "Storage and backup",
   "for": "Storage and backup administrators",
   "time": "3 hours",
   "steps": [
    {
     "module": "M6"
    },
    {
     "module": "M7"
    },
    {
     "module": "M9"
    },
    {
     "module": "M10",
     "only": [
      "DellCloudIQ"
     ]
    },
    {
     "module": "M12",
     "only": [
      "PhysicsAIFactory"
     ]
    },
    {
     "module": "E4"
    }
   ]
  },
  {
   "id": "datacenter-facilities",
   "title": "Power and cooling",
   "for": "Facilities, power and cooling teams",
   "time": "2 hours",
   "steps": [
    {
     "module": "M2"
    },
    {
     "module": "M3"
    },
    {
     "module": "M5"
    },
    {
     "module": "M4",
     "only": [
      "DellPowerEdgeXE9712"
     ]
    },
    {
     "module": "E1"
    },
    {
     "module": "M12",
     "only": [
      "PhysicsAIFactory"
     ]
    }
   ]
  },
  {
   "id": "security",
   "title": "Security and resilience",
   "for": "Security and resilience teams",
   "time": "2 hours",
   "steps": [
    {
     "module": "M2",
     "only": [
      "DellIDRAC"
     ]
    },
    {
     "module": "M9"
    },
    {
     "module": "M10",
     "only": [
      "DellNativeEdge"
     ]
    },
    {
     "module": "M8",
     "only": [
      "PhysicsFabric"
     ]
    }
   ]
  },
  {
   "id": "operations",
   "title": "Platform operations",
   "for": "Platform and operations teams",
   "time": "2 hours",
   "steps": [
    {
     "module": "M2"
    },
    {
     "module": "M10"
    },
    {
     "module": "M7",
     "only": [
      "DellPowerScale"
     ]
    },
    {
     "module": "M9",
     "only": [
      "DellPowerProtect"
     ]
    }
   ]
  },
  {
   "id": "executive-overview",
   "title": "The short version",
   "for": "Decision makers",
   "time": "45 minutes",
   "predictOnly": true,
   "register": "novice",
   "steps": [
    {
     "module": "M1"
    },
    {
     "module": "M4"
    },
    {
     "module": "M7"
    },
    {
     "module": "M9"
    },
    {
     "module": "M12"
    }
   ]
  },
  {
   "id": "what-goes-wrong",
   "title": "What goes wrong",
   "for": "Operators and anyone on call",
   "time": "90 minutes",
   "failuresOnly": true,
   "steps": [
    {
     "module": "M2",
     "only": [
      "DellIDRAC"
     ]
    },
    {
     "module": "M4",
     "only": [
      "DellPowerEdgeXE9712"
     ]
    },
    {
     "module": "M6",
     "only": [
      "DellPowerStore"
     ]
    },
    {
     "module": "M8",
     "only": [
      "DellPowerSwitchSN6000"
     ]
    },
    {
     "module": "M9",
     "only": [
      "DellPowerProtect",
      "DellCyberDetect"
     ]
    },
    {
     "module": "M10",
     "only": [
      "DellCloudIQ",
      "DellVxRail",
      "DellNativeEdge"
     ]
    },
    {
     "module": "E6",
     "only": [
      "DellAlienware"
     ]
    }
   ]
  },
  {
   "id": "electives",
   "title": "Electives",
   "for": "Anyone who has finished a track",
   "time": "10 to 15 minutes each",
   "steps": [
    {
     "module": "E1"
    },
    {
     "module": "E2"
    },
    {
     "module": "E3"
    },
    {
     "module": "E4"
    },
    {
     "module": "E5"
    },
    {
     "module": "E6"
    },
    {
     "module": "E7"
    }
   ]
  },
  {
   "id": "labs",
   "title": "Labs",
   "for": "Readers who want to be graded, not narrated",
   "time": "4 hours",
   "labsOnly": true,
   "steps": [
    {
     "module": "M3"
    },
    {
     "module": "M4"
    },
    {
     "module": "M5"
    },
    {
     "module": "M6"
    },
    {
     "module": "M7"
    },
    {
     "module": "M8"
    },
    {
     "module": "M9"
    },
    {
     "module": "M10"
    },
    {
     "module": "M11"
    },
    {
     "module": "M12"
    },
    {
     "module": "E1"
    },
    {
     "module": "E2"
    },
    {
     "module": "E3"
    },
    {
     "module": "E4"
    },
    {
     "module": "E6"
    },
    {
     "module": "E7"
    }
   ]
  }
 ]
};
