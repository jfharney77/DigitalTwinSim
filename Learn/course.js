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
    "standard": "Whether a kernel is limited by compute or by memory is a ratio, not a property of the chip.",
    "novice": "A chip can be held up by doing arithmetic or by waiting for data. Which one wins depends on how much arithmetic you get for each byte fetched, not on the chip alone."
   },
   "prereqs": [],
   "background": "A matrix multiply is N³ multiply-adds, and data has to be loaded before anything can use it.",
   "objectives": [
    "Define arithmetic intensity (multiply-adds per byte moved) and the ridge point.",
    "Predict the memory-bound or compute-bound regime from those two numbers.",
    "Explain why the playback clock lives in the browser and not in the engine."
   ],
   "entries": [
    {
     "twin": "GPU",
     "port": 5173,
     "name": "GPU die simulator",
     "links": [
      {
       "kind": "root",
       "label": "Open the simulator",
       "how": "Keep the Generic-128 profile and the matmul workload, set N to 4 and the tile size to 2, and read the regime. Then change only the data type, from fp32 to int8."
      },
      {
       "kind": "lesson",
       "hash": "#live/tour",
       "lesson": "the-roof",
       "label": "The CUDA lesson tour",
       "how": "Step forward to the lesson called Find the roof; it replays a bandwidth measurement against the simulator's roofline."
      }
     ]
    }
   ],
   "predict": {
    "q": {
     "standard": "Keep the matmul and the tile size the same and change only the data type, from fp32 to int8. Does the kernel stay memory-bound?",
     "novice": "Same job, same tiles. You only shrink each number from 4 bytes to 1 byte. Is the chip still waiting on memory?"
    },
    "options": [
     "Yes, it stays memory-bound",
     "No, it becomes compute-bound",
     "It depends on the clock speed"
    ],
    "answer": 1,
    "reveal": {
     "standard": "No. At fp32 it is memory-bound; at int8 the same workload is compute-bound. Fewer bytes carry the same multiply-adds, so intensity rises past the ridge point.",
     "novice": "No. Smaller numbers mean fewer bytes to fetch for the same amount of math, so the chip stops waiting on memory and starts waiting on its own arithmetic."
    },
    "cite": [
     "GPU/backend/tests/test_bandwidth.py::test_regime_flips_with_dtype"
    ]
   },
   "checks": [
    {
     "q": "Shrinking the tile moves arithmetic intensity which way, and why?",
     "a": "Down. A smaller tile reuses each loaded value fewer times, so more bytes move for the same multiply-adds.",
     "cite": [
      "GPU/backend/tests/test_bandwidth.py::test_smaller_tiles_lower_intensity_toward_memory_bound"
     ]
    },
    {
     "q": "In a memory-bound run, which total is larger: load cycles or compute cycles?",
     "a": "Load cycles. That is what memory-bound means in the trace.",
     "cite": [
      "GPU/backend/tests/test_bandwidth.py::test_regime_consistent_with_cycle_totals"
     ]
    },
    {
     "q": "Where does the timer that animates the die live?",
     "a": "In the browser, in GPU/frontend/src/App.tsx. The engine returns a finished list of states and holds no timers, which the component suite checks by parsing the engine's imports: nothing but pure modules is allowed in.",
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
    "standard": "A plugged-in server is never really off, and its slowest boot stage is teaching the memory to talk.",
    "novice": "As soon as a server is plugged in, a small management computer inside it is already running. The slow part of switching on is the memory learning its own timing."
   },
   "prereqs": [],
   "background": "A server has CPUs, memory modules (DIMMs), drives and fans.",
   "objectives": [
    "Put the power-on phases in order: off, standby, bmc, poweron, post, boot, os.",
    "Explain why the baseboard management controller (iDRAC) boots before the host.",
    "Name the longest stage and say why it cannot be skipped."
   ],
   "entries": [
    {
     "twin": "DellPowerEdgeR760",
     "port": 5174,
     "trace": "poweron",
     "name": "PowerEdge R760 power-on",
     "links": [
      {
       "kind": "tour",
       "id": "memory-training",
       "label": "Guided tour, at DDR5 memory training"
      },
      {
       "kind": "step",
       "value": 8,
       "expectPhase": "post",
       "label": "Power-on trace, paused on memory training"
      }
     ]
    },
    {
     "twin": "DellIDRAC",
     "port": 5177,
     "trace": "bringup",
     "name": "iDRAC9 bring-up",
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
       "label": "Bring-up trace, paused on Lifecycle Controller init"
      }
     ]
    }
   ],
   "predict": {
    "q": {
     "standard": "Which stage of the R760 power-on takes longest: the iDRAC boot, DDR5 memory training, or the operating system load?",
     "novice": "Switching on a server has several stages. Which one takes the longest: the helper computer starting, the memory checking itself, or the operating system loading?"
    },
    "options": [
     "The iDRAC boot",
     "DDR5 memory training",
     "The operating system load"
    ],
    "answer": 1,
    "reveal": {
     "standard": "DDR5 memory training, inside POST. The training step carries a cycle cost of 6, the unique maximum in the trace, and the player dwells on it.",
     "novice": "The memory checking itself. Every memory module has to learn its exact timing before the computer can trust it, and that takes longer than anything else."
    },
    "cite": [
     "DellPowerEdgeR760/backend/tests/test_engine.py::test_memory_training_is_the_longest_stage"
    ]
   },
   "checks": [
    {
     "q": "Does iDRAC come up before or after someone presses the power button?",
     "a": "Before. The bmc phase is steps 2 and 3, and poweron starts at step 4. The second bmc step takes a hardware inventory while the host is still off.",
     "cite": [
      "DellPowerEdgeR760/backend/tests/test_engine.py::test_trace_invariants"
     ]
    },
    {
     "q": "In the iDRAC twin, what is the most power the management domain ever draws?",
     "a": "8 W. The test allows up to 20 W, because the host never powers on during iDRAC's own bring-up.",
     "cite": [
      "DellIDRAC/backend/tests/test_engine.py::test_host_never_powers_on"
     ]
    },
    {
     "q": "Which iDRAC stage is the longest?",
     "a": "Lifecycle Controller initialization, step 8, with a cycle cost of 6.",
     "cite": [
      "DellIDRAC/backend/tests/test_engine.py::test_lifecycle_controller_is_the_longest_stage"
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
   }
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
   "background": "Power drawn by a server ends up as heat in the room.",
   "objectives": [
    "State the per-tick power balance: component watts sum to DC, and AC is DC divided by supply efficiency.",
    "Explain the fan-power feedback loop.",
    "Predict what losing a fan costs."
   ],
   "entries": [
    {
     "twin": "DellPowerEdgeR760Thermal",
     "port": 5203,
     "name": "R760 power and thermal simulator",
     "links": [
      {
       "kind": "scenario",
       "id": "fan-feedback",
       "title": "The fan-power feedback loop",
       "label": "The fan-power feedback loop"
      },
      {
       "kind": "scenario",
       "id": "kill-a-fan",
       "title": "Kill a fan",
       "label": "Kill a fan"
      }
     ]
    }
   ],
   "predict": {
    "q": {
     "standard": "The workload never changes. Three minutes in, the inlet air rises to 40 °C. Does the server's power draw go up, stay flat, or go down?",
     "novice": "The server keeps doing exactly the same work. Then the room gets hot. Does the server start using more electricity, the same, or less?"
    },
    "options": [
     "It goes up",
     "It stays flat, because the work is the same",
     "It goes down"
    ],
    "answer": 0,
    "reveal": {
     "standard": "It goes up. The fans spin faster to hold the silicon at temperature, and fan watts are part of the DC sum on every tick.",
     "novice": "It goes up. The fans have to spin faster to keep the chips cool, and the fans' own electricity is part of the bill."
    },
    "cite": [
     "DellPowerEdgeR760Thermal/backend/tests/test_engine.py::test_power_balance_every_tick"
    ]
   },
   "checks": [
    {
     "q": "Kill two of six fans under HPC load on the Balanced build. Do the CPUs throttle?",
     "a": "No. The four survivors spin faster and the CPUs keep their clocks.",
     "cite": [
      "DellPowerEdgeR760Thermal/backend/tests/test_engine.py::test_fan_failure_survivors_ramp"
     ]
    },
    {
     "q": "Why can five fans at a higher speed use more power than six at a lower speed?",
     "a": "Fan power scales with the cube of speed, while airflow scales only linearly with it.",
     "cite": [
      "DellPowerEdgeR760Thermal/backend/tests/test_engine.py::test_power_balance_every_tick"
     ]
    },
    {
     "q": "At steady state, what sets the air's temperature rise through the box?",
     "a": "ΔT = DC / (ṁ·cp): the heat divided by the mass flow of air times its heat capacity.",
     "cite": [
      "DellPowerEdgeR760Thermal/backend/tests/test_engine.py::test_heat_balance_at_steady_state"
     ]
    }
   ],
   "pins": [],
   "bridge": {
    "text": {
     "standard": "One R760 moves its heat with air. An eight-GPU server draws around 11 kW, and at that density air starts to run out. The next module scales the box up.",
     "novice": "One ordinary server can be cooled with fans. Servers packed with GPUs make far more heat. Next, see what changes when a box holds eight GPUs, then a whole rack holds seventy-two."
    },
    "next": "M4"
   }
  },
  {
   "id": "M4",
   "title": "Eight GPUs, then seventy-two",
   "core": true,
   "idea": {
    "standard": "The NVLink domain fuses all at once, and where its wall sits is the design decision.",
    "novice": "The fast links between GPUs join them into one big GPU in a single moment. Whether that group stops at the edge of one box or one rack is the choice that shapes everything else."
   },
   "prereqs": [
    "M2",
    "M3"
   ],
   "background": "A server boots its host first, and fans are part of the load.",
   "objectives": [
    "Explain why the NVLink domain appears all at once.",
    "Locate the domain wall: the chassis for the XE9680, the rack for the XE9712.",
    "Explain liquid before silicon."
   ],
   "entries": [
    {
     "twin": "DellPowerEdgeXE9680",
     "port": 5201,
     "trace": "poweron",
     "name": "PowerEdge XE9680 (eight GPUs)",
     "links": [
      {
       "kind": "tour",
       "id": "domain-stops-at-eight",
       "label": "Guided tour, where the domain stops at eight"
      },
      {
       "kind": "phase",
       "value": "fuse",
       "label": "Power-on trace, at the fuse"
      },
      {
       "kind": "phase",
       "value": "fabric",
       "label": "Power-on trace, as the NICs join"
      }
     ]
    },
    {
     "twin": "DellPowerEdgeXE9712",
     "port": 5181,
     "trace": "poweron",
     "name": "PowerEdge XE9712 (GB200 NVL72 rack)",
     "links": [
      {
       "kind": "tour",
       "id": "atomic-fuse",
       "label": "Guided tour, at the atomic fuse"
      },
      {
       "kind": "tour",
       "id": "liquid-before-silicon",
       "label": "Guided tour, at liquid before silicon"
      },
      {
       "kind": "phase",
       "value": "fused",
       "label": "Power-on trace, at the fuse"
      }
     ]
    },
    {
     "twin": "PhysicsCompute",
     "port": 5205,
     "name": "AI compute physics",
     "links": [
      {
       "kind": "scenario",
       "id": "air-vs-liquid",
       "title": "Air vs liquid",
       "label": "Air vs liquid"
      }
     ]
    }
   ],
   "predict": {
    "q": {
     "standard": "An XE9712 rack brings up 72 GPUs across its trays. As they train their links, does the count of GPUs in the NVLink domain climb gradually (8, 16, 32 and so on) or jump?",
     "novice": "A rack has 72 GPUs that are about to be joined into one. Do they join a few at a time, or all at once?"
    },
    "options": [
     "It climbs a tray at a time",
     "It jumps from 0 to 72 in one step",
     "It stops at 8, one server's worth"
    ],
    "answer": 1,
    "reveal": {
     "standard": "It jumps from 0 to 72 in one step, at the fused phase, and never takes an intermediate value. A partial domain would be a different machine.",
     "novice": "All at once. The count is 0 right up until the moment it is 72. Half-joined is not a state the rack ever shows."
    },
    "cite": [
     "DellPowerEdgeXE9712/backend/tests/test_engine.py::test_fuse_joins_all_72_gpus_at_once"
    ]
   },
   "checks": [
    {
     "q": "In the XE9680, which comes first: the eight NICs joining the fabric, or the NVLink fuse?",
     "a": "The fuse. The domain reaches 8 at step 4 while no NIC is up, and the NICs reach 8 at step 5. The domain never grows past 8.",
     "cite": [
      "DellPowerEdgeXE9680/backend/tests/test_engine.py::test_the_fuse_is_atomic_and_the_domain_stops_at_eight",
      "DellPowerEdgeXE9680/backend/tests/test_engine.py::test_one_nic_per_gpu_joins_the_fabric_after_the_fuse"
     ]
    },
    {
     "q": "What does the XE9712 do before any tray boots?",
     "a": "It starts coolant flow. The coolant phase is step 2 and trayboot is step 3.",
     "cite": [
      "DellPowerEdgeXE9712/backend/tests/test_engine.py::test_coolant_flows_before_any_silicon"
     ]
    },
    {
     "q": "Which stage is longest in each twin, and why do they differ?",
     "a": "XE9680: gpuinit (cost 5, training the memory on eight GPUs). XE9712: fabric (cost 5, training NVLink over the copper spine). The XE9680's fuse runs over board traces and needs no cable training.",
     "cite": [
      "DellPowerEdgeXE9680/backend/tests/test_engine.py::test_gpu_init_is_the_longest_stage",
      "DellPowerEdgeXE9712/backend/tests/test_engine.py::test_fabric_training_is_the_longest_stage"
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
    }
   ],
   "bridge": {
    "text": {
     "standard": "The XE9712 pauses at coolant until the loop proves itself. The IR7000's verify phase is what it is waiting for. The next module is that loop.",
     "novice": "The big rack will not switch on its GPUs until the cooling liquid is flowing. Next, look at the cooling loop itself."
    },
    "next": "M5"
   }
  },
  {
   "id": "M5",
   "title": "Liquid: heat in equals heat out",
   "core": true,
   "idea": {
    "standard": "A cooling loop is a device for making three numbers equal, and coordination decides what gives when it cannot.",
    "novice": "Every watt of heat the computers make has to leave through the water or the air, exactly. When the water can't keep up, something has to slow down, and it matters who decides."
   },
   "prereqs": [
    "M3",
    "M4"
   ],
   "background": "The heat identity in air, and liquid before silicon.",
   "objectives": [
    "State the heat balance: liquid plus air equals IT load, exactly.",
    "Explain flow before heat.",
    "Compare what a rack controller does on a warm-water day with what happens without one."
   ],
   "entries": [
    {
     "twin": "DellIR7000",
     "port": 5182,
     "trace": "thermal",
     "name": "IR7000 liquid-cooled rack",
     "links": [
      {
       "kind": "tour",
       "id": "heat-balance",
       "label": "Guided tour, at the heat balance"
      },
      {
       "kind": "phase",
       "value": "verify",
       "label": "Thermal trace, at leak and flow verification"
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
     "links": [
      {
       "kind": "scenario",
       "id": "warm-water-day",
       "title": "Warm water day (coordinated)",
       "label": "Warm water day (coordinated)"
      },
      {
       "kind": "scenario",
       "id": "warm-water-panic",
       "title": "Warm water day (panic)",
       "label": "Warm water day (panic)"
      }
     ]
    }
   ],
   "predict": {
    "q": {
     "standard": "Building water arrives 6 °C warmer. In one run the rack controller coordinates; in the other, each bank of trays protects only itself. Which run keeps more banks online?",
     "novice": "The water coming from the building gets warmer. In one version a controller tells every group of servers to slow down a little. In the other, each group looks after itself. Which keeps more servers running?"
    },
    "options": [
     "The coordinated run",
     "The uncoordinated run",
     "They end up the same"
    ],
    "answer": 0,
    "reveal": {
     "standard": "The coordinated run keeps all six banks online with zero trips by capping every bank a little. The uncoordinated run trips at least two banks and sheds more compute than the physics required, because the loop's lag keeps the survivors hot after the first trip.",
     "novice": "The coordinated one. Everyone slows a little and nothing shuts down. Without coordination, groups shut off one after another and more work is lost than the warm water ever demanded."
    },
    "cite": [
     "PhysicsCDU/backend/tests/test_engine.py::test_acceptance_warm_water_day_coordinated_sheds_gracefully",
     "PhysicsCDU/backend/tests/test_engine.py::test_acceptance_warm_water_day_uncoordinated_cascades"
    ]
   },
   "checks": [
    {
     "q": "At IR7000 steady state, what share of the 264 kW leaves through the liquid?",
     "a": "240 kW, about 91%. The other 24 kW goes to air, and the two sum exactly on every step.",
     "cite": [
      "DellIR7000/backend/tests/test_engine.py::test_heat_balance_holds_on_every_step",
      "DellIR7000/backend/tests/test_engine.py::test_liquid_carries_the_overwhelming_share"
     ]
    },
    {
     "q": "Why is the flow already 300 L/min while the IT load is still zero?",
     "a": "Flow has to exist before the first watt of heat does.",
     "cite": [
      "DellIR7000/backend/tests/test_engine.py::test_flow_before_heat"
     ]
    },
    {
     "q": "Which IR7000 stage is longest?",
     "a": "verify, with a cycle cost of 5: the per-branch leak and flow check.",
     "cite": [
      "DellIR7000/backend/tests/test_engine.py::test_verification_is_the_longest_stage"
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
     "field": "flow_lpm",
     "value": 300
    },
    {
     "twin": "DellIR7000",
     "step": 2,
     "field": "it_load_watts",
     "value": 0
    }
   ],
   "bridge": {
    "text": {
     "standard": "The rack is powered, fused and cooled, and now it wants data. The next module starts with the arithmetic every storage system pays.",
     "novice": "The machines are on and cool. Now they need data. Next: what it really costs to save something to disk."
    },
    "next": "M6"
   }
  },
  {
   "id": "M6",
   "title": "Storage arithmetic and the mirrored ack",
   "core": true,
   "idea": {
    "standard": "Every write costs more than one write, and an acknowledged write already lives in two places.",
    "novice": "Saving one piece of data makes the disks do several jobs. And when the storage says \"saved\", the data is already kept in two places in case one fails."
   },
   "prereqs": [],
   "background": "A drive can fail.",
   "objectives": [
    "Compute the RAID write penalty.",
    "Explain why the write acknowledgement comes from NVRAM, not from the drives.",
    "Explain the dual-node lockstep."
   ],
   "entries": [
    {
     "twin": "PhysicsME5",
     "port": 5214,
     "name": "PowerVault ME5 RAID physics",
     "links": [
      {
       "kind": "scenario",
       "id": "write-penalty",
       "title": "RAID write penalty",
       "label": "RAID write penalty"
      },
      {
       "kind": "scenario",
       "id": "second-failure",
       "title": "Second failure, mid-rebuild",
       "label": "Second failure, mid-rebuild"
      }
     ]
    },
    {
     "twin": "DellPowerStore",
     "port": 5175,
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
       "label": "Power-on trace, as the NVRAM write cache initializes"
      }
     ]
    }
   ],
   "predict": {
    "q": {
     "standard": "Same drives, a saturating pure-write load. RAID 10 against RAID 6: how far apart are the served write IOPS?",
     "novice": "Two ways of protecting the same disks. The disks are as busy as they can be, doing only saves. How much faster does the first way (RAID 10) save than the second (RAID 6)?"
    },
    "options": [
     "About the same",
     "About 1.5 times",
     "Exactly 3 times",
     "About 6 times"
    ],
    "answer": 2,
    "reveal": {
     "standard": "Exactly 3×. RAID 10 costs 2 backend I/Os per write and RAID 6 costs 6.",
     "novice": "Three times. Each save costs RAID 10 two disk jobs and RAID 6 six disk jobs."
    },
    "cite": [
     "PhysicsME5/backend/tests/test_engine.py::test_write_penalty_ratio_r10_vs_r6"
    ]
   },
   "checks": [
    {
     "q": "A second drive fails mid-rebuild. Which survives, RAID 5 or RAID 6?",
     "a": "RAID 6. It carries two parity blocks, so it can lose a second drive inside the rebuild window.",
     "cite": [
      "PhysicsME5/backend/tests/test_engine.py::test_second_failure_mid_rebuild_r6_survives_r5_does_not"
     ]
    },
    {
     "q": "During PowerStore's power and boot phases, can node A light a region without node B lighting its twin?",
     "a": "No. Every lit -a region lights its -b twin; the nodes come up in lockstep.",
     "cite": [
      "DellPowerStore/backend/tests/test_engine.py::test_dual_node_bring_up_is_symmetric"
     ]
    },
    {
     "q": "Which PowerStore stage is longest?",
     "a": "The PowerStoreOS container boot at step 5, with a cycle cost of 4.",
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
    }
   ],
   "bridge": {
    "text": {
     "standard": "PowerStore puts two controllers in front of the drives, and every byte passes through one of them. The next module is about what happens when you delete that controller.",
     "novice": "This storage has two brains in front of its disks, and all data goes through them. Next: storage designs that get rid of that middle layer."
    },
    "next": "M7"
   }
  },
  {
   "id": "M7",
   "title": "Deleting the controller",
   "core": true,
   "idea": {
    "standard": "Scale-out storage removes one thing (the controller, the volume, or the metadata hop), and the whole design follows from it.",
    "novice": "Big storage systems get simpler by removing one piece: the middleman, the fixed-size box, or the lookup on every read. Each design follows from what it removed."
   },
   "prereqs": [
    "M6"
   ],
   "background": "Controllers and rebuilds.",
   "objectives": [
    "Explain why rebuilds get faster as a scale-out pool grows.",
    "Say what having no volumes means for growth.",
    "Explain why the metadata server leaves the data path."
   ],
   "entries": [
    {
     "twin": "DellPowerFlex",
     "port": 5189,
     "trace": "cluster",
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
       "label": "Cluster trace, at the rebuild"
      }
     ]
    },
    {
     "twin": "DellPowerScale",
     "port": 5196,
     "trace": "namespace",
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
       "label": "Namespace trace, at add node"
      }
     ]
    },
    {
     "twin": "DellExascale",
     "port": 5184,
     "trace": "datapath",
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
       "label": "Data-path trace, at the layout"
      },
      {
       "kind": "phase",
       "value": "feed",
       "label": "Data-path trace, at full feed"
      }
     ]
    },
    {
     "twin": "PhysicsStorage",
     "port": 5206,
     "name": "Storage physics",
     "links": [
      {
       "kind": "scenario",
       "id": "scale-out-rebuild",
       "title": "Scale-up vs scale-out rebuild",
       "label": "Scale-up vs scale-out rebuild"
      }
     ]
    }
   ],
   "predict": {
    "q": {
     "standard": "One of six PowerFlex nodes dies. How many nodes do the rebuild work: one, two, or all five survivors?",
     "novice": "A storage pool is spread over six servers and one of them breaks. How many of the remaining servers help rebuild the lost copies?"
    },
    "options": [
     "One spare node",
     "Two partner nodes",
     "All five survivors"
    ],
    "answer": 2,
    "reveal": {
     "standard": "All five survivors. At the rebuild step the number of rebuild participants equals the number of nodes online. In a controller array that number is one at any size, which is why a bigger pool here rebuilds faster.",
     "novice": "All five. Every server that is left helps, so the bigger the pool, the faster the repair."
    },
    "cite": [
     "DellPowerFlex/backend/tests/test_engine.py::test_every_surviving_node_rebuilds"
    ]
   },
   "checks": [
    {
     "q": "Does PowerFlex I/O stop during the failure?",
     "a": "No. IOPS go from 1,800k to 1,620k at the failure and 1,500k during the rebuild, then back to 1,800k. They never fall below 70% of steady.",
     "cite": [
      "DellPowerFlex/backend/tests/test_engine.py::test_service_survives_the_failure"
     ]
    },
    {
     "q": "PowerScale grows from 4 to 6 nodes at addnode. What happens to migrations required and to used percent?",
     "a": "Migrations stay at 0. Capacity goes from 400 to 600 TB, and used falls from 81% to 54% without moving or deleting anything.",
     "cite": [
      "DellPowerScale/backend/tests/test_engine.py::test_growing_the_cluster_requires_no_migration",
      "DellPowerScale/backend/tests/test_engine.py::test_capacity_grows_with_nodes_not_with_planning"
     ]
    },
    {
     "q": "In which Exascale phases is the metadata server active?",
     "a": "Exactly mount and layout. It is absent from every bulk phase, while throughput peaks at 48,000 Gb/s with all four data servers streaming.",
     "cite": [
      "DellExascale/backend/tests/test_engine.py::test_metadata_leaves_the_data_path",
      "DellExascale/backend/tests/test_engine.py::test_peak_throughput_reaches_rack_scale"
     ]
    },
    {
     "q": "In the physics app, does a 20-node cluster rebuild faster than a 5-node cluster, and faster than a dual-controller array?",
     "a": "Faster than both. Rebuild rate grows with the number of survivors.",
     "cite": [
      "PhysicsStorage/backend/tests/test_engine.py::test_rebuild_faster_with_more_nodes_and_the_inversion"
     ]
    }
   ],
   "pins": [
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
     "twin": "DellExascale",
     "agg": "max",
     "field": "throughput_gbps",
     "value": 48000
    }
   ],
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
    "standard": "Ethernet proves losslessness under stress; InfiniBand makes loss impossible to express.",
    "novice": "One kind of network reacts fast to traffic jams so nothing gets lost. The other never sends anything until the receiver says it has room, so nothing can get lost."
   },
   "prereqs": [
    "M4",
    "M7"
   ],
   "background": "NVLink stops at the chassis or rack wall, so scale-out traffic is the fabric's job; incast.",
   "objectives": [
    "Contrast reactive losslessness (ECN and PFC plus adaptive routing) with credit-based flow control.",
    "Explain SHARP's crossing counters.",
    "Recognize a gray failure."
   ],
   "entries": [
    {
     "twin": "DellPowerSwitchSN6000",
     "port": 5185,
     "trace": "fabric",
     "name": "PowerSwitch SN6000 Ethernet fabric",
     "links": [
      {
       "kind": "tour",
       "id": "zero-drops-under-stress",
       "label": "Guided tour, at zero drops under stress"
      },
      {
       "kind": "phase",
       "value": "congestion",
       "label": "Fabric trace, at congestion"
      }
     ]
    },
    {
     "twin": "DellQuantumX800",
     "port": 5202,
     "trace": "fabric",
     "name": "Quantum-X800 InfiniBand fabric",
     "links": [
      {
       "kind": "tour",
       "id": "credits-before-bytes",
       "label": "Guided tour, at credits before bytes"
      },
      {
       "kind": "tour",
       "id": "sharp-counters-cross",
       "label": "Guided tour, as the SHARP counters cross"
      },
      {
       "kind": "phase",
       "value": "burst",
       "label": "Fabric trace, at the incast burst"
      }
     ]
    },
    {
     "twin": "PhysicsFabric",
     "port": 5207,
     "name": "Fabric physics",
     "links": [
      {
       "kind": "scenario",
       "id": "gray-failure",
       "title": "Gray failure",
       "label": "Gray failure"
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
     "q": "When SHARP turns on in the Quantum-X800 twin, what happens to fabric traffic and to the effective all-reduce rate?",
     "a": "Fabric traffic falls from 36 to 22 Tb/s while the all-reduce rate rises from 1,600 to 2,900 Gb/s. The math moved into the switches.",
     "cite": [
      "DellQuantumX800/backend/tests/test_engine.py::test_sharp_moves_the_math_into_the_fabric"
     ]
    },
    {
     "q": "What does the incast burst cost InfiniBand, if not drops?",
     "a": "Stalls: 1,800 µs per second, on the burst step only. Packets sent without a credit stay at 0 everywhere.",
     "cite": [
      "DellQuantumX800/backend/tests/test_engine.py::test_the_burst_stalls_senders_instead_of_losing_work",
      "DellQuantumX800/backend/tests/test_engine.py::test_no_packet_is_ever_sent_without_a_credit"
     ]
    },
    {
     "q": "In the physics app, what does the status panel show after a gray failure?",
     "a": "All green, with zero dropped packets counted, while delivered throughput falls and flow completion time rises more than 1.5×.",
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
     "step": 7,
     "field": "allreduce_gbps",
     "value": 2900
    },
    {
     "twin": "DellQuantumX800",
     "step": 8,
     "field": "stall_micros_per_sec",
     "value": 1800
    }
   ],
   "bridge": {
    "text": {
     "standard": "A gray failure is damage the dashboard does not show. Ransomware has the same shape, so the next module starts from the question the gray link raises: what can you still trust?",
     "novice": "Some problems don't show up on the dashboard at all. Ransomware is like that. Next: how to keep a safe copy, prove it is clean, and keep attackers away from it."
    },
    "next": "M9"
   }
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
   "background": "Snapshots and deduplication.",
   "objectives": [
    "Tell apart isolation (does a copy survive), integrity (is the copy clean) and access (who can reach the data).",
    "Explain why recovery time is set by the decision plus the bandwidth."
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
       "label": "Lifecycle trace, at the attack"
      }
     ]
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
       "label": "Guided tour, blind then reading"
      },
      {
       "kind": "phase",
       "value": "blind",
       "label": "Detection trace, while metadata is blind"
      },
      {
       "kind": "phase",
       "value": "verdict",
       "label": "Detection trace, at the verdict"
      }
     ]
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
       "value": "breach",
       "label": "Access trace, at the breach"
      }
     ]
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
       "label": "Backups aren't enough"
      },
      {
       "kind": "scenario",
       "id": "rto-surprise",
       "title": "The RTO surprise",
       "label": "The RTO surprise"
      }
     ]
    }
   ],
   "predict": {
    "q": {
     "standard": "Ransomware encrypts snapshots over several days. How many alerts does metadata-based detection raise before byte-level inspection runs?",
     "novice": "Ransomware quietly scrambles saved copies over several days. A monitor watches file names and activity, not the contents. How many alarms does it raise?"
    },
    "options": [
     "Zero",
     "One, on the first encrypted snapshot",
     "One per encrypted snapshot"
    ],
    "answer": 0,
    "reveal": {
     "standard": "Zero. At the blind step 4 of 7 snapshots are corrupted and metadata alerts are still 0. Confidence stays at 0 until inspection has run, then jumps to 99%, and the verdict names snapshot 3 as the last clean copy.",
     "novice": "None. Four of seven copies are already damaged and the monitor is silent. Only reading the actual bytes finds it, and the answer is a date: the last clean copy."
    },
    "cite": [
     "DellCyberDetect/backend/tests/test_engine.py::test_metadata_detection_is_blind_while_corruption_spreads",
     "DellCyberDetect/backend/tests/test_engine.py::test_confidence_comes_only_from_reading_content",
     "DellCyberDetect/backend/tests/test_engine.py::test_the_named_copy_is_actually_clean"
    ]
   },
   "checks": [
    {
     "q": "In PowerProtect, in which phases is the air gap open?",
     "a": "Only replicate and recover. During the attack no vault region and no gap region is active.",
     "cite": [
      "DellPowerProtect/backend/tests/test_engine.py::test_air_gap_discipline",
      "DellPowerProtect/backend/tests/test_engine.py::test_attack_cannot_reach_the_vault"
     ]
    },
    {
     "q": "What dedupe ratio does PowerProtect's trace reach?",
     "a": "20:1: 500 TB logical stored in 25 TB. The test requires at least 10:1.",
     "cite": [
      "DellPowerProtect/backend/tests/test_engine.py::test_dedupe_economics"
     ]
    },
    {
     "q": "In Fort Zero the attacker holds an inside position at breach. How many resources can it reach?",
     "a": "None. Implicit trust grants are 0 on every step, and even a legitimate grant reaches at most one resource, on a 300-second lease.",
     "cite": [
      "DellFortZero/backend/tests/test_engine.py::test_the_breach_reaches_nothing",
      "DellFortZero/backend/tests/test_engine.py::test_the_breach_is_actually_inside",
      "DellFortZero/backend/tests/test_engine.py::test_least_privilege_is_literal"
     ]
    },
    {
     "q": "In the physics app, why does a 200 TB restore at 1 GB/s take days even with a clean copy?",
     "a": "Recovery time is the decision time plus terabytes divided by bandwidth. The test pins it above 48 hours.",
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
   "bridge": {
    "text": {
     "standard": "Every one of these depended on someone watching. The next module is the watching, and the rest of the operations bill.",
     "novice": "All of this only works if someone is paying attention. Next: running and watching a whole estate of machines."
    },
    "next": "M10"
   }
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
   "background": "iDRAC's out-of-band management, and clusters.",
   "objectives": [
    "Follow telemetry to an insight.",
    "Contrast hyperconverged coupling (VxRail) with disaggregated pools (Private Cloud).",
    "Explain zero-touch as attestation first.",
    "Price manual against automated operations."
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
     ]
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
     ]
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
     ]
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
     ]
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
       "label": "The 3-node trap"
      },
      {
       "kind": "scenario",
       "id": "catalog-vs-artisanal",
       "title": "Catalog vs artisanal",
       "label": "Catalog vs artisanal"
      }
     ]
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
     "standard": "Nothing. Storage goes from 200 to 400 TB at growstorage and compute stays at 48 units. On VxRail a new node would have brought processors whether or not you needed them.",
     "novice": "Nothing changes. Storage doubles and computing stays exactly where it was, because the two are bought separately. In an all-in-one design, extra storage arrives with extra processors attached."
    },
    "cite": [
     "DellPrivateCloud/backend/tests/test_engine.py::test_compute_and_storage_scale_independently",
     "DellPrivateCloud/backend/tests/test_engine.py::test_nothing_scales_that_was_not_asked_for"
    ]
   },
   "checks": [
    {
     "q": "How many VxRail nodes light during primary election?",
     "a": "Exactly one, n1, which breaks the lockstep the other phases keep.",
     "cite": [
      "DellVxRail/backend/tests/test_engine.py::test_primary_election_lights_exactly_one_node"
     ]
    },
    {
     "q": "How many human actions does a NativeEdge site take?",
     "a": "One: power and a cable, at the power step. Nothing comes online until attestation establishes trust, and attestation is the longest stage.",
     "cite": [
      "DellNativeEdge/backend/tests/test_engine.py::test_exactly_one_human_action",
      "DellNativeEdge/backend/tests/test_engine.py::test_nothing_runs_before_trust_is_established",
      "DellNativeEdge/backend/tests/test_engine.py::test_attestation_is_the_longest_stage"
     ]
    },
    {
     "q": "What does CloudIQ's health score do across the pipeline?",
     "a": "It starts at 100, dips to 71 at detect, and ends at 88 at notify: recovered, but not back to 100.",
     "cite": [
      "DellCloudIQ/backend/tests/test_engine.py::test_health_starts_perfect_dips_on_detection_then_recovers"
     ]
    },
    {
     "q": "In the physics app, same fleet and same faults, run manually against automated: how many more admin hours does manual take?",
     "a": "More than five times as many.",
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
   "bridge": {
    "text": {
     "standard": "One endpoint in a NativeEdge estate is a Pro Max Plus workstation running a model with no network at all. The next module opens it and returns to the roofline from the first module.",
     "novice": "One of those edge machines could be a laptop running an AI model with no internet. Next: why that works, which goes back to the very first module."
    },
    "next": "M11"
   }
  },
  {
   "id": "M11",
   "title": "Inference at the edge",
   "core": true,
   "idea": {
    "standard": "Decode is memory-bound, so the winning move is to never move the weights again.",
    "novice": "Generating text is limited by fetching the model from memory, so the trick is to load the model once, keep it right next to the chip, and never move it again."
   },
   "prereqs": [
    "M1"
   ],
   "background": "The memory-bound regime.",
   "objectives": [
    "Explain why the weights cross the PCIe link once.",
    "Connect decode to the memory-bound regime.",
    "Separate token rate from tokens per joule."
   ],
   "entries": [
    {
     "twin": "DellProMaxPlus",
     "port": 5186,
     "trace": "inference",
     "name": "Pro Max Plus with a discrete NPU",
     "links": [
      {
       "kind": "tour",
       "id": "weights-cross-once",
       "label": "Guided tour, as the weights cross once"
      },
      {
       "kind": "phase",
       "value": "load",
       "label": "Inference trace, at the model load"
      },
      {
       "kind": "phase",
       "value": "offline",
       "label": "Inference trace, with the network unplugged"
      }
     ]
    },
    {
     "twin": "PhysicsClient",
     "port": 5204,
     "name": "Client device physics",
     "links": [
      {
       "kind": "scenario",
       "id": "three-engines",
       "title": "Same model, three engines",
       "label": "Same model, three engines"
      }
     ]
    }
   ],
   "predict": {
    "q": {
     "standard": "During generation, how much traffic crosses the PCIe link between the host and the inference card?",
     "novice": "The AI card is generating text. How much data travels between the laptop and the card while it does?"
    },
    "options": [
     "A steady stream of weights",
     "Bursts, one per token",
     "None"
    ],
    "answer": 2,
    "reveal": {
     "standard": "None. The link carries 52 Gb/s only during load (61 GB of weights) and 0 on every other step, including all of decode.",
     "novice": "None. The model is copied onto the card once at the start, and after that the link sits idle."
    },
    "cite": [
     "DellProMaxPlus/backend/tests/test_engine.py::test_weights_cross_the_link_exactly_once",
     "DellProMaxPlus/backend/tests/test_engine.py::test_weights_are_monotonic_and_never_evicted"
    ]
   },
   "checks": [
    {
     "q": "What changes at the final offline step, when the network is unplugged?",
     "a": "Nothing. Tokens per second stay at 21.",
     "cite": [
      "DellProMaxPlus/backend/tests/test_engine.py::test_disconnecting_the_network_changes_nothing"
     ]
    },
    {
     "q": "In the physics app, ranked by token rate and by tokens per joule, where do CPU, GPU and NPU land?",
     "a": "Rate: GPU, then NPU, then CPU. Efficiency: NPU, then GPU, then CPU.",
     "cite": [
      "PhysicsClient/backend/tests/test_engine.py::test_npu_wins_tokens_per_joule"
     ]
    },
    {
     "q": "Why is decode memory-bound?",
     "a": "Each generated token re-reads the weights and the KV cache for very few multiply-adds, so intensity falls below the ridge. The GPU twin's llm_decode workload pins the fall and the regime flip.",
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
     "step": 7,
     "field": "tokens_per_second",
     "value": 21
    }
   ],
   "bridge": {
    "text": {
     "standard": "The Pro Max Plus wins by refusing to move data. An AI factory can't refuse: its data has to arrive, and when it doesn't, every other module's hardware waits. The capstone couples them all.",
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
   "background": "Everything so far; the security module is recommended.",
   "objectives": [
    "Reason from coupled subsystems to the six headline instruments.",
    "Show that starvation, checkpoint cost and the power budget come out of the trace rather than being set as parameters.",
    "Map a real deployment onto the modules."
   ],
   "entries": [
    {
     "twin": "PhysicsAIFactory",
     "port": 5219,
     "name": "AI factory capstone",
     "links": [
      {
       "kind": "scenario",
       "id": "stand-up",
       "title": "Stand up an AI factory",
       "label": "Stand up an AI factory"
      },
      {
       "kind": "scenario",
       "id": "starved-cluster",
       "title": "The starved cluster",
       "label": "The starved cluster"
      },
      {
       "kind": "scenario",
       "id": "checkpoint-goldilocks",
       "title": "Checkpoint Goldilocks",
       "label": "Checkpoint Goldilocks"
      },
      {
       "kind": "scenario",
       "id": "warm-day",
       "title": "Warm day at 90% of budget",
       "label": "Warm day at 90% of budget"
      }
     ]
    },
    {
     "twin": "PhysicsCompute",
     "port": 5205,
     "name": "AI compute physics",
     "links": [
      {
       "kind": "scenario",
       "id": "starved",
       "title": "Starved GPUs",
       "label": "Starved GPUs"
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
     "standard": "Tokens per second fall to about half and GPU idle due to data rises to about 50%. Power does not fall with them: a starved GPU still draws most of its power, which is where the waste comes from.",
     "novice": "Work drops to about half, but the electricity bill barely moves. A waiting GPU still uses most of its power, so starving it wastes money."
    },
    "cite": [
     "PhysicsAIFactory/backend/tests/test_engine.py::test_starvation_emerges_from_the_arithmetic",
     "PhysicsCompute/backend/tests/test_engine.py::test_data_starvation_cuts_tokens_more_than_watts"
    ]
   },
   "checks": [
    {
     "q": "Checkpoint every 5, 60 or 480 minutes: which yields the most tokens?",
     "a": "60. Too often taxes every hour; too rarely loses more on each rollback.",
     "cite": [
      "PhysicsAIFactory/backend/tests/test_engine.py::test_checkpoint_goldilocks_interior_optimum"
     ]
    },
    {
     "q": "On the warm day, can facility power exceed the budget?",
     "a": "No. The engine sheds GPU clocks so facility power sits on the ceiling.",
     "cite": [
      "PhysicsAIFactory/backend/tests/test_engine.py::test_facility_never_exceeds_budget",
      "PhysicsAIFactory/backend/tests/test_engine.py::test_warm_day_sheds_load_and_logs_it"
     ]
    },
    {
     "q": "Where does the dice roll for GPU failures happen?",
     "a": "Nowhere. Failures arrive on MTBF arithmetic and roll the token counter back to the last checkpoint; the engine is not allowed to import random.",
     "cite": [
      "PhysicsAIFactory/backend/tests/test_engine.py::test_failures_arrive_on_the_mtbf_schedule_and_roll_back_tokens"
     ]
    }
   ],
   "pins": [],
   "bridge": {
    "text": {
     "standard": "Reopen the Colossus page with the modules behind you. Each block links to a twin you have now played. The page's note box separates what the sources state from what the drawing invents, and that habit is the last lesson.",
     "novice": "Now open the Colossus page again. You have played every model it links to. Notice how the page separates facts from drawings; keeping those apart is the last lesson."
    },
    "next": null
   }
  },
  {
   "id": "E1",
   "title": "Rack power: the runtime the battery really has",
   "core": false,
   "idea": {
    "standard": "A UPS front panel believes its nameplate watt-hours until a self-test tells it otherwise.",
    "novice": "A backup battery's display trusts the number printed on the box until someone tests the battery for real."
   },
   "prereqs": [],
   "background": "",
   "objectives": [],
   "entries": [
    {
     "twin": "PhysicsRackPower",
     "port": 5217,
     "name": "Rack PDU and UPS physics",
     "links": [
      {
       "kind": "scenario",
       "id": "old-batteries",
       "title": "The 4-year-old batteries",
       "label": "The 4-year-old batteries"
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
     "q": "After four VRLA years, is the pack above or below 80% of nameplate?",
     "a": "Below. The test requires the capacity fraction to be under 0.8.",
     "cite": [
      "PhysicsRackPower/backend/tests/test_engine.py::test_old_batteries_runtime_gap_is_the_capacity_fraction"
     ]
    },
    {
     "q": "Moving loads between phases: does it change the total power?",
     "a": "No. It changes the imbalance and relieves phase A, and the PDU input stays the same.",
     "cite": [
      "PhysicsRackPower/backend/tests/test_engine.py::test_balance_the_phases_moves_conserve_and_relieve"
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
   "id": "E2",
   "title": "Shared chassis: the noisy neighbor",
   "core": false,
   "idea": {
    "standard": "One hot sled taxes the chassis fans for all eight bays.",
    "novice": "In a chassis where eight servers share the fans, one busy server makes the fans work harder for everyone."
   },
   "prereqs": [],
   "background": "",
   "objectives": [],
   "entries": [
    {
     "twin": "PhysicsMX7000",
     "port": 5212,
     "name": "MX7000 modular chassis physics",
     "links": [
      {
       "kind": "scenario",
       "id": "noisy-neighbor",
       "title": "The noisy neighbor, thermally",
       "label": "The noisy neighbor, thermally"
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
     "q": "Which slot does the fan controller target?",
     "a": "The hottest one: slot 1, the noisy sled.",
     "cite": [
      "PhysicsMX7000/backend/tests/test_engine.py::test_noisy_neighbor_taxes_the_shared_fans"
     ]
    },
    {
     "q": "With N+1 PSU redundancy, does the chassis survive losing a whole AC feed?",
     "a": "No. N+1 covers a supply dying, not a feed dying; grid redundancy rides through the same event.",
     "cite": [
      "PhysicsMX7000/backend/tests/test_engine.py::test_nplus1_does_not_survive_a_feed_loss",
      "PhysicsMX7000/backend/tests/test_engine.py::test_grid_redundancy_survives_a_whole_feed_loss"
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
   "id": "E3",
   "title": "Rugged edge: the filter nobody changed",
   "core": false,
   "idea": {
    "standard": "A fouled filter turns a heat wave the server could survive into one it throttles through.",
    "novice": "A dusty air filter can be the difference between a server coping with a hot day and a server slowing down."
   },
   "prereqs": [],
   "background": "",
   "objectives": [],
   "entries": [
    {
     "twin": "PhysicsXR",
     "port": 5213,
     "name": "PowerEdge XR rugged edge physics",
     "links": [
      {
       "kind": "scenario",
       "id": "filter-nobody-changed",
       "title": "The filter nobody changed",
       "label": "The filter nobody changed"
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
     "q": "At constant work, what does fouling cost?",
     "a": "Fan power. The fans spin faster to push the same air, while CPU power is unchanged.",
     "cite": [
      "PhysicsXR/backend/tests/test_engine.py::test_fouling_costs_fan_power_at_constant_work"
     ]
    },
    {
     "q": "What happens right after a clean-filter event?",
     "a": "Fouling drops to 0 and the fans relax.",
     "cite": [
      "PhysicsXR/backend/tests/test_engine.py::test_clean_filter_event_restores_airflow"
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
   "id": "E4",
   "title": "Dedupe as arithmetic: the entropy alarm",
   "core": false,
   "idea": {
    "standard": "The entropy of today's changed data raises the alarm within days; capacity notices weeks later.",
    "novice": "Encrypted data looks like random noise. Watching for that noise in each day's backup catches ransomware long before the disks fill up."
   },
   "prereqs": [],
   "background": "",
   "objectives": [],
   "entries": [
    {
     "twin": "PhysicsDataDomain",
     "port": 5215,
     "name": "Data Domain dedupe physics",
     "links": [
      {
       "kind": "scenario",
       "id": "entropy-alarm",
       "title": "Entropy as a smoke alarm",
       "label": "Entropy as a smoke alarm"
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
     "Entropy, within days",
     "Capacity, within days",
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
     "q": "Data that is already high-entropy but static: does it dedupe?",
     "a": "Yes, it still dedupes, but it does not compress.",
     "cite": [
      "PhysicsDataDomain/backend/tests/test_engine.py::test_static_high_entropy_still_dedupes_but_does_not_compress"
     ]
    },
    {
     "q": "Is the dedupe ratio a setting?",
     "a": "No. It is the quotient of logical over physical, and physical is a ledger that must balance every day.",
     "cite": [
      "PhysicsDataDomain/backend/tests/test_engine.py::test_capacity_conservation_every_day"
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
   "id": "E5",
   "title": "Modernize without migrating",
   "core": false,
   "idea": {
    "standard": "A new generation joins a live cluster with zero downtime; the 3× only arrives after cutover.",
    "novice": "New storage hardware joins the old while everything keeps running, and the speed-up only shows once the switch-over is done."
   },
   "prereqs": [],
   "background": "",
   "objectives": [],
   "entries": [
    {
     "twin": "DellPowerStoreElite",
     "port": 5220,
     "trace": "join",
     "name": "PowerStore Elite cluster join",
     "links": [
      {
       "kind": "tour",
       "id": "zero-downtime-join",
       "label": "Guided tour, at the zero-downtime join"
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
     "A few seconds per volume",
     "Minutes, during cutover"
    ],
    "answer": 0,
    "reveal": {
     "standard": "None, on every step. The rebalance may tax service, never stop it: IOPS stay above 85% of baseline.",
     "novice": "Not at all. Things may run a bit slower during the move, but they never stop."
    },
    "cite": [
     "DellPowerStoreElite/backend/tests/test_engine.py::test_downtime_is_always_zero",
     "DellPowerStoreElite/backend/tests/test_engine.py::test_service_never_pauses"
    ]
   },
   "checks": [
    {
     "q": "When does the cluster serve at least 3× its baseline?",
     "a": "Only from cutover on. Before cutover it stays at or below 1.2× baseline.",
     "cite": [
      "DellPowerStoreElite/backend/tests/test_engine.py::test_performance_triples_only_after_cutover"
     ]
    },
    {
     "q": "When does effective capacity jump?",
     "a": "Exactly once, at the join.",
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
   "background": "",
   "objectives": [],
   "entries": [
    {
     "twin": "DellAlienware",
     "port": 5176,
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
     "Yes, throttled and not charging",
     "No, it refuses to boot",
     "Yes, at full speed"
    ],
    "answer": 0,
    "reveal": {
     "standard": "Yes. Charge power is 0 throughout, CPU plus GPU stay at or under 40 W even at full load, and the phase machine still ends at steady with the throttled regime.",
     "novice": "Yes. It won't charge and it runs slowly, but it still works."
    },
    "cite": [
     "DellAlienware/backend/tests/test_engine.py::test_unrecognized_adapter_is_throttled"
    ]
   },
   "checks": [
    {
     "q": "Does the battery level rise with an unrecognized adapter?",
     "a": "No. Charging is disabled everywhere, so the battery never rises above where it started.",
     "cite": [
      "DellAlienware/backend/tests/test_engine.py::test_unrecognized_adapter_is_throttled"
     ]
    },
    {
     "q": "Starting deeply discharged, in what order does charging go?",
     "a": "Precharge, then constant current, then constant voltage.",
     "cite": [
      "DellAlienware/backend/tests/test_engine.py::test_charge_ramp_stages_in_order"
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
   "id": "E7",
   "title": "The data pipeline: the bottleneck moves",
   "core": false,
   "idea": {
    "standard": "Throughput is the minimum of the stages, so fixing one stage moves the bottleneck somewhere else.",
    "novice": "A pipeline runs only as fast as its slowest step. Speed up that step and a different step becomes the slowest."
   },
   "prereqs": [],
   "background": "",
   "objectives": [],
   "entries": [
    {
     "twin": "PhysicsData",
     "port": 5210,
     "name": "Data pipeline physics",
     "links": [
      {
       "kind": "scenario",
       "id": "find-the-bottleneck",
       "title": "Find the bottleneck",
       "label": "Find the bottleneck"
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
     "q": "If arrival stays above the constraint, what grows?",
     "a": "The backlog at the constraint and the freshness lag: days-old data, with no error message.",
     "cite": [
      "PhysicsData/backend/tests/test_engine.py::test_backlog_and_freshness_grow_when_arrival_exceeds_the_constraint"
     ]
    },
    {
     "q": "What does a serving shortfall show up as?",
     "a": "GPU idle due to data above 20%.",
     "cite": [
      "PhysicsData/backend/tests/test_engine.py::test_gpu_idle_reflects_serving_shortfall"
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
  }
 ]
};
