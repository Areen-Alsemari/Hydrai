# Project Handoff --- Physics-Informed AI Agent for Predictive Hydrogen Storage Safety

> **Purpose:** Self-contained context for another LLM, researcher,
> engineer, or developer. This file consolidates the project goal, scope
> decisions, architecture, data strategy, digital-twin plan, ML tasks,
> agent role, engineering inputs, equations, schemas, evaluation plan,
> and open decisions. The reader should be able to continue the project
> without the user re-explaining prior discussions.

------------------------------------------------------------------------

## 1. Project in One Sentence

We want to build a **physics-informed AI safety agent for hydrogen
storage systems** that continuously monitors sensor behavior, **detects
abnormal pressure/temperature/flow behavior, identifies emerging
hydrogen leakage, forecasts developing unsafe conditions, cross-checks
predictions against physics, explains the risk, and recommends an
operator response**.

**Physical storage system / Digital Twin → Sensor Data → ML Models →
Physics Verification → Safety Agent → Operator**

The project combines two challenge areas:

-   **Smart pressure and temperature monitoring**
-   **Reducing hydrogen leakage risk through early detection and
    predictive risk assessment**

------------------------------------------------------------------------

## 2. Challenge Context

The original hydrogen-storage challenge highlights leakage, safety
risks, energy loss, cost, transport/distribution difficulty, and the
need for more efficient, safe, sustainable storage.

Possible focus areas were:

-   Reduce leakage risk
-   Facilitate transport/distribution
-   Smart pressure/temperature monitoring
-   Improve storage insulation

The selected direction is **smart monitoring + leakage risk**, because
these form one coherent AI/time-series safety product.

------------------------------------------------------------------------

## 3. Final Product Concept

### Working name

**AI Agent for Predictive Hydrogen Storage Safety**

### Technical description

> A physics-informed AI safety agent that continuously monitors hydrogen
> storage systems, detects abnormal sensor behavior, diagnoses whether
> an anomaly is consistent with hydrogen leakage or another fault,
> forecasts whether the system is approaching unsafe conditions,
> verifies the result against physical models, and provides an
> explainable risk assessment and recommended operator action.

### Core behavior

**Detect → Diagnose → Predict → Verify → Assess → Explain → Recommend**

The MVP is a **decision-support and supervised-intervention system**,
not an uncertified autonomous emergency controller.

------------------------------------------------------------------------

## 4. Critical Scope Decision: What "Predict Leakage" Means

There are two different problems.

### A. IN SCOPE --- emerging leak detection / prediction from system behavior

Evidence may include:

-   Pressure trajectory deviates from expected behavior
-   Inlet/outlet mass flow becomes inconsistent
-   Temperature exhibits an abnormal transient
-   External H₂ concentration increases
-   Behavior is inconsistent with the current operating mode

The system should detect the developing event and estimate whether it is
progressing toward an unsafe state.

### B. OUT OF SCOPE FOR V1 --- predicting material failure before a leak exists

That would mean:

**Hydrogen exposure → embrittlement/material degradation → crack
nucleation → crack growth → vessel failure → leakage**

This requires a different structural-integrity/materials problem
involving alloy composition, hydrogen diffusion, fatigue, crack growth,
fracture toughness, welds, defects, stress history, microstructure, etc.

### Role of material/alloy in V1

Material is **not ignored**. Engineers should provide material
properties where they affect:

-   Heat transfer
-   Thermal mass
-   Vessel behavior
-   Allowable P/T operating envelope

But V1 does **not** predict crack formation or hydrogen embrittlement
from alloy properties.

------------------------------------------------------------------------

## 5. Recommended Canonical Physical System

Current recommendation: use a **compressed gaseous hydrogen storage
system** as the canonical product environment, subject to final
engineering confirmation.

Potential components:

-   High-pressure H₂ vessel
-   Inlet/outlet lines
-   Valves
-   Pressure regulator
-   Relief/vent system
-   Pressure sensor(s)
-   Temperature sensor(s)
-   Inlet/outlet mass-flow sensors
-   External H₂ concentration detector
-   Relevant control/operating states

The engineering team must freeze the final topology and provide a
schematic/P&ID.

------------------------------------------------------------------------

## 6. Why a Digital Twin Is Central

There is unlikely to be one public dataset containing all ideal
variables across many real storage experiments:

-   Pressure
-   Temperature
-   Inlet/outlet flow
-   H₂ concentration
-   Valve states
-   Operating mode
-   Leak size/location
-   Sensor faults
-   Normal operation
-   Overpressure/overtemperature
-   Developing leaks
-   Confusing non-leak faults

Merging unrelated datasets directly into one training table would be
scientifically weak because they represent different systems, sensors,
ranges, sampling rates, and operating conditions.

The intended strategy is:

**Real experimental data**\
↓ calibrate / validate\
**Physics-based digital twin**\
↓ generate coherent controlled scenarios\
**Multivariate time-series dataset**\
↓ train ML\
**Independent experimental evidence**\
↓ test physical credibility/generalization

This is a **hybrid physics + data approach**, not random synthetic-data
generation.

------------------------------------------------------------------------

## 7. Data Strategy

### Layer 1 --- Real experimental storage data

Use real hydrogen-storage experiments to understand/validate normal
behavior:

-   Pressure trajectories
-   Temperature trajectories
-   H₂ flow
-   Charging/filling
-   Discharging
-   Idle/storage behavior
-   Transients

A previously identified example is **HSR-Rig-Project**, with variables
such as timestamp, pressure, Temp1/Temp2, H₂ flow, cumulative H₂
transferred, strain, and absorption/desorption phases.

**Important:** this represents a storage-reactor/metal-hydride
environment and should not redefine the final product if the canonical
system is compressed gaseous storage. Use it only where physically
relevant. Verify licensing before commercial reuse.

### Layer 2 --- Public hydrogen-system anomaly data

Previously identified: **H2-SimNet**, containing multiple pressure/flow
sensors and labeled hydrogen-system anomalies.

Possible use:

-   Multivariate anomaly-detection methodology
-   Fault classification/localization
-   Sensor robustness
-   Overlapping anomalies

Limitation: hydrogen-blend transport infrastructure is not identical to
a storage vessel.

### Layer 3 --- Hydrogen leak/release numerical and CFD data

Previously identified datasets contain combinations of:

-   Initial pressure
-   Leak/orifice diameter
-   Mass flow
-   Pressure evolution
-   Spatial pressure probes

Use for:

-   Leak-signature modeling
-   Leak severity methodology
-   Forecasting
-   Digital-twin/physics validation

Never call numerical/CFD data experimental.

### Layer 4 --- Experimental leak/release literature

Real high-pressure H₂ release experiments can be used as validation
targets even when raw downloadable data are unavailable.

Do not scrape plots and present them as clean experimental training data
without a defensible methodology.

### Layer 5 --- Physics/property resources

Previously discussed:

-   **HyRAM+** --- hydrogen release/safety/risk physics toolkit
-   Credible hydrogen real-gas/property models
-   NIST REFPROP if appropriately licensed
-   Open property implementations where suitable

HyRAM+ is primarily a **physics/risk engine**, not simply a dataset.
Software/data licensing must be checked before commercial distribution.

------------------------------------------------------------------------

## 8. Digital-Twin Data Should Be Episodes, Not Random Rows

Example:

``` text
0–200 s      normal filling
200–350 s    stable operation
350 s        micro-leak begins
350–450 s    developing leakage
450–500 s    external H₂ concentration increases
500+ s       unsafe state
```

Confusing negative example:

``` text
normal
→ cooling/heater fault
→ temperature changes
→ pressure changes
→ NO LEAK
```

Sensor-fault example:

``` text
normal
→ pressure sensor drift
→ apparent pressure anomaly
→ underlying physics remains normal
→ SENSOR FAULT
```

This prevents the model from learning simplistic rules such as
**pressure drop = leak**.

------------------------------------------------------------------------

## 9. Target Dataset Schema

``` yaml
episode_id:
timestamp:

system_context:
  operating_mode:
  valve_states:
  target_pressure:
  target_temperature:

measurements:
  pressure:
  temperature:
  inlet_mass_flow:
  outlet_mass_flow:
  external_h2_concentration:

optional_measurements:
  additional_pressure_sensors:
  additional_temperature_sensors:
  ambient_temperature:
  ambient_pressure:

simulation_ground_truth:
  true_h2_mass:
  leak_mass_flow:
  leak_area:
  leak_location:
  physical_fault_state:

labels:
  anomaly:
  event_type:
  severity:
  safety_state:
  time_to_unsafe:
```

Some simulation-ground-truth variables are for training/evaluation only
and would not be available to the deployed AI.

------------------------------------------------------------------------

## 10. Sensors

P/T are central but should not be the only leak evidence.

### Core

-   Pressure
-   Temperature
-   Inlet mass flow
-   Outlet mass flow

### Strongly desirable

-   External H₂ concentration sensor

### Context

-   Valve/regulator state
-   Operating mode
-   Ambient conditions where relevant

Mass-flow balance is informative:

\[ `\dot `{=tex}m\_{in} - `\dot `{=tex}m\_{out} \]

Unexpected mass loss combined with abnormal P/T behavior increases leak
plausibility. External H₂ sensing provides independent evidence.

------------------------------------------------------------------------

## 11. Governing Physics Engineers Must Provide or Approve

The engineering team need not derive everything from scratch. They must
specify/approve the correct formulation, assumptions, parameters,
references, and valid ranges.

### 11.1 Mass balance

\[
`\frac{dm}{dt}`{=tex}=`\dot `{=tex}m\_{in}-`\dot `{=tex}m\_{out}-`\dot `{=tex}m\_{leak}
\]

Confirm any additional mass-transfer terms.

### 11.2 Hydrogen equation of state

\[ P=f(`\rho`{=tex},T) \]

Do not blindly assume (PV=nRT) at high pressure. Engineers must approve
the real-gas EOS/property model and valid P/T range.

### 11.3 Energy balance

Conceptually:

\[ `\frac{dU}{dt}`{=tex} =
`\dot `{=tex}Q+`\dot `{=tex}m\_{in}h\_{in}-`\dot `{=tex}m\_{out}h\_{out}-`\dot `{=tex}m\_{leak}h\_{leak}
+`\text{applicable terms}`{=tex} \]

Define:

-   Vessel-wall heat transfer
-   Hydrogen-wall exchange
-   Ambient heat transfer
-   Wall thermal mass
-   Filling heating
-   Expansion cooling
-   Neglected terms

### 11.4 Leak/release model

\[
`\dot `{=tex}m\_{leak}=f(P,T,A\_{leak},P\_{ambient},C_d,`\ldots`{=tex})
\]

Engineers should define/approve:

-   Choked/unchoked treatment
-   Transition criterion
-   Discharge coefficient (C_d)
-   Effective leak area
-   Pressure-ratio treatment
-   Real-gas correction
-   Applicable correlations/ranges

Physical propagation should be:

\[
A\_{leak}`\rightarrow`{=tex}`\dot `{=tex}m\_{leak}`\rightarrow `{=tex}m(t)`\rightarrow `{=tex}P(t),T(t)
\]

not arbitrary pressure subtraction.

### 11.5 Valve/regulator flow

\[
`\dot `{=tex}m=f(`\text{valve state}`{=tex},P\_{up},P\_{down},T,`\ldots`{=tex})
\]

Provide characteristic curves/correlations or approved simplified logic.

### 11.6 External H₂ concentration

\[
C\_{H_2}(x,t)=f(`\dot `{=tex}m\_{leak},`\text{geometry}`{=tex},`\text{ventilation}`{=tex},`\text{sensor location}`{=tex},`\ldots`{=tex})
\]

Engineering team should approve the fidelity: e.g. well-mixed enclosure
vs dispersion model. Do not invent arbitrary ppm readings.

------------------------------------------------------------------------

## 12. Scenario Classes

### Normal modes --- subject to engineering confirmation

-   Filling
-   Storage/idle
-   Discharge
-   Depressurization
-   Startup
-   Shutdown

### Leak scenarios should vary

-   Leak location
-   Orifice size
-   Initial pressure/temperature
-   Sudden vs progressive leak
-   Leak growth law
-   Operating mode at onset
-   Duration
-   Environment/ventilation
-   Sensor noise/placement

### Non-leak faults

Ask engineers to validate: - Cooling failure - Heating fault - Valve
malfunction - Regulator malfunction - Blocked/restricted line - Abnormal
filling/discharge - Overpressure - Relief activation - Other
system-specific faults

### Sensor faults

AI/data team can model: - Bias - Drift - Dropout - Stuck-at - Random
noise - Calibration error

------------------------------------------------------------------------

## 13. Example Patterns the Model Must Distinguish

  ------------------------------------------------------------------------------------
  Event        Pressure    Temperature   Flow             External H₂ True state
  ------------ ----------- ------------- ---------------- ----------- ----------------
  Normal       ↓           may ↓         expected         normal      NORMAL
  discharge                                                           

  Cooling      ↓           ↓             normal           normal      NORMAL/THERMAL

  Micro-leak   slight      transient     unexplained      may ↑       LEAK
               abnormal ↓                imbalance                    

  Larger leak  rapid       transient     strong imbalance ↑           LEAK
               abnormal ↓                                             

  Heater fault ↑           strong ↑      normal           normal      THERMAL FAULT

  Valve event  variable    variable      mode-dependent   normal      CONTROL/FLOW

  P-sensor     apparent    normal        normal           normal      SENSOR FAULT
  drift        deviation                                              
  ------------------------------------------------------------------------------------

Exact behaviors and labels must be engineering-approved.

------------------------------------------------------------------------

## 14. ML Architecture

Do not initially use one giant model.

### Model A --- Anomaly Detection

Question: **Is current behavior inconsistent with expected operation?**

Possible baselines: - Statistical/residual methods - Isolation Forest -
Autoencoder - Temporal autoencoder - Other multivariate time-series
anomaly methods

Output example:

``` json
{"anomaly_score": 0.84}
```

### Model B --- Fault Diagnosis

Question: **If abnormal, what is most likely happening?**

Initial classes may include:

``` text
NORMAL
LEAK
THERMAL_FAULT
PRESSURE_FAULT
FLOW_OR_CONTROL_FAULT
SENSOR_FAULT
```

Output:

``` json
{"event":"possible_hydrogen_leak","probability":0.91}
```

### Model C --- Forecasting / Early Warning

Given recent history (X\_{t-k:t}), predict future:

\[ P\_{t+1:t+n}, `\quad `{=tex}T\_{t+1:t+n} \]

and/or:

\[ P(`\text{unsafe state within prediction horizon}`{=tex}) \]

Potential approaches: - Classical baselines - LSTM - TCN - Temporal
Transformer if justified

Goal: warn **before** a threshold is crossed when the trajectory
indicates developing danger.

------------------------------------------------------------------------

## 15. Physics Verification Layer

ML outputs should be cross-checked against physics/digital twin:

``` text
AI prediction
    ↓
Physics consistency check
    ↓
Confidence / contradiction signal
```

Questions include:

-   Is predicted P response consistent with estimated mass loss?
-   Is leak explanation consistent with flow imbalance?
-   Are P/T changes plausible for the operating state?
-   Does release physics support inferred severity?

The agent/LLM is not the source of physical truth.

------------------------------------------------------------------------

## 16. Safety Agent

The agent receives structured evidence from:

-   Anomaly model
-   Fault classifier
-   Forecast model
-   Physics engine
-   Operating state
-   Safety rules

Example:

``` json
{
  "anomaly_score": 0.89,
  "fault_class": "possible_leak",
  "leak_probability": 0.91,
  "pressure_trend": "decreasing_abnormally",
  "flow_imbalance": true,
  "external_h2": "increasing",
  "forecast": {
    "risk": "high",
    "horizon_seconds": 120
  },
  "physics_check": "consistent"
}
```

Agent role:

**Observe → Correlate → Verify → Assess → Explain → Recommend**

The LLM should not diagnose a leak directly from raw sensor numbers
without ML/physics evidence.

------------------------------------------------------------------------

## 17. Safety/Control Boundary

For MVP:

-   Agent recommends actions.
-   Operator may approve a simulated intervention.
-   Digital twin can demonstrate valve/isolation effects.
-   Do **not** claim an uncertified generative AI autonomously controls
    a real high-pressure vessel.

Preferred positioning:

**AI decision support + supervised intervention**

Real emergency shutdown remains under appropriate certified
safety/control systems.

------------------------------------------------------------------------

## 18. Ideal Demo

1.  Digital twin runs normally.
2.  Dashboard shows live P/T/flow/H₂.
3.  Small simulated leak is injected.
4.  Anomaly score increases.
5.  Fault model identifies likely leak.
6.  Forecast predicts deterioration before critical threshold.
7.  Physics layer confirms consistency.
8.  Agent explains the evidence.
9.  Agent recommends approved isolation response.
10. Operator clicks **Approve** in simulation.
11. Digital twin changes valve state.
12. Risk trajectory improves.
13. Agent reports decreasing risk and continues monitoring.

This is a dynamic decision-support demo, not a chatbot demo.

------------------------------------------------------------------------

## 19. Evaluation

### Detection

-   Recall/sensitivity
-   Precision
-   F1
-   AUROC
-   AUPRC
-   False alarms per operating hour

### Early warning

-   Detection delay
-   Lead time before unsafe threshold
-   Smallest reliably detected leak
-   Performance across leak sizes/pressures/modes

### Forecasting

-   Pressure MAE/RMSE
-   Temperature MAE/RMSE
-   Unsafe-state prediction performance
-   Probability calibration where applicable

### Robustness

-   Noise
-   Drift
-   Dropout
-   Unseen leak sizes
-   Unseen initial pressures
-   Unseen operating combinations
-   Non-leak faults that resemble leaks

### Physics consistency

Measure violations/disagreement with known physical constraints.

### Split rule

**Split by scenario/episode, not random rows.**

Do not put portions of one trajectory in both train and test. Prefer
unseen episodes/configurations in test.

------------------------------------------------------------------------

# 20. EXACT ENGINEERING INPUTS REQUIRED

Engineers define **what is physically true**. The AI team must not
invent these values.

## 20.1 System Definition

``` yaml
storage_type:
vessel_type:
hydrogen_state:
application:
stationary_or_mobile:
system_boundary:
```

Also provide schematic/P&ID showing vessel, inlet/outlet, valves,
regulators, relief devices, vents, sensors, and connections.

## 20.2 Geometry

``` yaml
internal_volume_L:
relevant_dimensions:
wall_thickness_mm:
inlet_diameter_mm:
outlet_diameter_mm:
vent_diameter_mm:
port_geometry:
```

## 20.3 Pressure

``` yaml
nominal_pressure_bar:
minimum_operating_pressure_bar:
maximum_operating_pressure_bar:
filling_pressure_bar:
MAWP_bar:
design_pressure_bar:
warning_pressure_bar:
critical_pressure_bar:
```

## 20.4 Temperature

``` yaml
normal_temperature_min_C:
normal_temperature_max_C:
filling_temperature_range_C:
discharge_temperature_range_C:
ambient_temperature_min_C:
ambient_temperature_max_C:
warning_temperature_C:
critical_temperature_C:
```

## 20.5 Flow

``` yaml
normal_fill_mass_flow_kg_s:
maximum_fill_mass_flow_kg_s:
normal_discharge_mass_flow_kg_s:
maximum_discharge_mass_flow_kg_s:
fill_flow_profile:
discharge_flow_profile:
```

## 20.6 Material --- V1-relevant only

``` yaml
liner_material:
structural_material:
thermal_conductivity:
specific_heat:
density:
other_thermal_or_operating_properties:
```

Detailed fracture/embrittlement properties are not required unless scope
changes.

## 20.7 Thermal Characteristics

Provide/approve:

-   Wall thermal conductivity
-   Wall heat capacity
-   Wall density
-   H₂-wall heat-transfer assumptions
-   External convection assumptions
-   Ambient boundary conditions
-   Whether wall thermal mass is explicitly modeled

## 20.8 Hydrogen Property Model

Specify/approve:

-   Real-gas EOS/property model
-   Accepted correlations/library
-   P/T validity range
-   Simplifying assumptions

## 20.9 Normal Operating Modes

For every mode:

``` yaml
mode_name:
initial_pressure:
initial_temperature:
initial_h2_mass:
target_pressure:
target_temperature:
inlet_flow_profile:
outlet_flow_profile:
valve_configuration:
expected_duration:
expected_pressure_behavior:
expected_temperature_behavior:
normal_allowable_variation:
transition_condition:
```

## 20.10 Control Logic

Provide:

-   Valve logic
-   Regulator behavior
-   Setpoints
-   Relief-device behavior
-   Control response logic
-   Characteristic curves/correlations if available

## 20.11 Leak Scenarios

For each:

``` yaml
leak_location:
physical_cause:
effective_leak_diameter_or_area:
initial_pressure:
initial_temperature:
sudden_or_progressive:
leak_growth_law_if_progressive:
expected_flow_regime:
expected_duration:
expected_h2_detector_response:
severity:
unsafe_criterion:
approved_operator_response:
```

Engineers define severity, not AI team.

## 20.12 Other Faults

``` yaml
fault_name:
component:
physical_cause:
affected_variables:
expected_pressure_response:
expected_temperature_response:
expected_flow_response:
expected_h2_response:
severity:
warning_criterion:
critical_criterion:
approved_operator_response:
```

## 20.13 Sensors

For every sensor:

``` yaml
sensor_name:
sensor_type:
location:
measured_variable:
units:
measurement_range:
accuracy:
resolution:
sampling_frequency:
response_time:
latency:
expected_noise:
```

Candidate sensors: - Pressure - Temperature - Inlet flow - Outlet flow -
External H₂ concentration

## 20.14 Environment / Boundaries

``` yaml
ambient_pressure:
ambient_temperature_range:
enclosure_volume_if_applicable:
ventilation_rate_or_assumption:
downstream_pressure:
other_boundary_conditions:
```

## 20.15 Safety Envelope and Labels

Engineers define measurable physical criteria for:

``` text
NORMAL
WARNING
CRITICAL
NORMAL_OPERATION
LEAK
THERMAL_FAULT
PRESSURE_FAULT
FLOW_OR_CONTROL_FAULT
SENSOR_FAULT
```

## 20.16 Validation Targets

Provide trusted:

-   Experimental curves/data
-   Manufacturer data
-   Engineering calculations
-   Standards
-   Peer-reviewed experiments
-   Accepted reference simulations

## 20.17 Causal Relationships

Example leak chain:

\[ A\_{leak}`\uparrow`{=tex} `\rightarrow`{=tex}
`\dot `{=tex}m\_{leak}`\uparrow`{=tex} `\rightarrow`{=tex}
`\text{unexpected mass loss}`{=tex} `\rightarrow`{=tex}
P(t)`\text{ deviation}`{=tex} `\rightarrow`{=tex}
T(t)`\text{ transient}`{=tex} `\rightarrow`{=tex}
C\_{H_2}`\text{ may increase}`{=tex} `\rightarrow`{=tex}
`\text{risk increases}`{=tex} \]

These causal models help ground agent explanations.

------------------------------------------------------------------------

# 21. ENGINEERING DELIVERABLES

## Deliverable 01 --- System Definition Pack

-   One-page physical-system description
-   Storage technology/use case
-   System boundary
-   Schematic/P&ID
-   Component topology

## Deliverable 02 --- Parameter Workbook

-   Geometry
-   P/T envelope
-   Flow ranges/profiles
-   V1-relevant material properties
-   Thermal properties
-   Environment/boundary conditions

## Deliverable 03 --- Physics Model Pack

For each subsystem: - Equation/correlation - Constants/coefficients -
Assumptions - Valid range - Source/reference - Approved simplifications

Include mass balance, energy balance, EOS, leak/release, valve/regulator
flow, heat transfer, and H₂ concentration/dispersion if used.

## Deliverable 04 --- Operating Scenario Matrix

For each normal mode: - Initial/boundary conditions - Flow profiles -
Valve/control states - Expected P/T/flow behavior - Allowable
variation - Transition rules

## Deliverable 05 --- Leak & Fault Matrix

For each event: - Location/component - Cause - Parameter range -
Physical behavior - Sensor effects - Severity - Warning/critical
criteria - Approved response

## Deliverable 06 --- Instrumentation Specification

For every sensor: - Type/location - Units/range - Accuracy/resolution -
Sampling - Response time - Expected noise

## Deliverable 07 --- Safety & Label Specification

Engineering definitions for: - NORMAL/WARNING/CRITICAL - Leak severity -
Fault classes - Unsafe-state criteria - Approved operator actions

## Deliverable 08 --- Validation Evidence Pack

Trusted evidence for digital-twin validation: - Experimental data -
Manufacturer specifications - Standards - Literature - Engineering
calculations - Accepted simulations

------------------------------------------------------------------------

## 22. Acceptance Condition Before Final ML Training

Do not begin **final** ML training until:

1.  Physical system boundary is fixed.
2.  Governing physics/ranges are approved.
3.  Normal scenarios are defined.
4.  Leak/non-leak fault scenarios are defined.
5.  Sensor specifications are defined.
6.  Safety labels are physically justified.
7.  Digital-twin outputs are checked against credible validation
    evidence.
8.  Episode-level train/validation/test strategy is fixed.

Exploratory ML can happen earlier but should not be presented as final
product performance.

------------------------------------------------------------------------

## 23. Responsibility Split

### Engineering team --- defines physical truth

Owns: - System definition - Physical parameters -
Equations/correlations - Operating modes - Failure scenarios - Safety
thresholds - Instrumentation assumptions - Validation targets

### Digital-twin/data team --- encodes and generates

Owns: - Twin implementation - Scenario generation - Sensor noise/fault
injection - Processing/windows/labels - Dataset QA

### ML team --- learns sensor patterns

Owns: - Anomaly detection - Fault diagnosis - Forecasting -
Calibration - Robustness testing - Evaluation

### Agent/application team --- turns evidence into operator support

Owns: - Evidence aggregation - Risk reasoning - Explanation -
Recommendations - Dashboard - Human approval workflow - Logging/audit
trail

**Engineers define reality → Digital twin encodes reality → Data team
generates trajectories → ML learns patterns → Physics verifies → Agent
interprets/recommends.**

------------------------------------------------------------------------

## 24. What NOT to Do

1.  Do not call every pressure drop a leak.
2.  Do not train only on normal vs leak; include confusing faults.
3.  Do not let an LLM determine leak physics from raw sensor numbers.
4.  Do not generate arbitrary synthetic rows without physics.
5.  Do not merge unrelated datasets as if they came from one system.
6.  Do not use ideal-gas assumptions at high pressure without
    justification.
7.  Do not invent safety thresholds.
8.  Do not randomly split rows from the same episode across train/test.
9.  Do not claim material-degradation prediction in V1.
10. Do not claim uncertified AI autonomously operates real high-pressure
    safety equipment.
11. Do not call simulated/CFD data experimental.
12. Do not assume public access equals commercial-use permission; check
    licenses.

------------------------------------------------------------------------

## 25. Product Positioning

### Concise description

> **A physics-informed predictive safety layer for hydrogen storage
> infrastructure. It fuses pressure, temperature, flow, hydrogen-sensor,
> and operating-state data to detect abnormal behavior, diagnose
> potential leakage, forecast unsafe trajectories, verify findings
> against physical models, and provide operators with explainable risk
> assessments and recommended actions.**

### Short pitch

> Traditional monitoring often reacts when a sensor crosses a fixed
> threshold. This system aims to understand **how the storage system is
> behaving and where it is heading**. By combining multivariate sensor
> intelligence with hydrogen physics, it can distinguish normal
> operational changes from emerging leakage or other faults and warn
> operators before a developing condition becomes critical.

------------------------------------------------------------------------

## 26. Technical/Research Contribution

The contribution is not merely **"AI detects hydrogen leaks."**

The stronger contribution is integration of:

1.  Physics-based digital twin
2.  Multivariate time-series anomaly detection
3.  Fault diagnosis
4.  Unsafe-state forecasting
5.  Physics consistency verification
6.  Agentic explainability/decision support
7.  Scenario-based validation under sensor faults, noise, and unseen
    conditions

Think:

**Physics + AI + Agent**

not:

**Dataset + classifier + chatbot**

------------------------------------------------------------------------

## 27. Open Decisions

Do not silently assume these.

### Physical system

-   Confirm compressed gaseous H₂ storage
-   Define vessel class/type/size
-   Define P/T envelope
-   Define topology

### Physics

-   Select/approve EOS
-   Select leak/release model
-   Select heat-transfer fidelity
-   Decide H₂ dispersion fidelity
-   Define valve/regulator models

### Instrumentation

-   Confirm realistic sensors
-   Sensor placement/sampling
-   Decide whether external H₂ sensor is mandatory

### Scenarios

-   Leak-size ranges
-   Progressive leak model if included
-   Non-leak fault catalogue
-   Normal modes

### Safety

-   Engineering/standards-based warning/critical criteria
-   Approved operator actions
-   Severity taxonomy

### Data

-   Re-audit public datasets for files, variables, units, licenses, and
    commercial-use constraints
-   Decide calibration vs external-validation sources
-   Do not let a mismatched dataset redefine the product

### ML

-   Establish simple baselines first
-   Select prediction horizon(s)
-   Define episode-level splits
-   Define acceptable recall, false alarms, and warning lead time

------------------------------------------------------------------------

## 28. Immediate Next Steps

1.  Engineering team completes system/physics/safety specification.
2.  Freeze representative compressed-H₂ storage system.
3.  Build first-principles digital-twin baseline.
4.  Validate normal P/T/flow trajectories.
5.  Add controlled leak/release physics.
6.  Add confusing non-leak faults.
7.  Add realistic sensor characteristics/noise/faults.
8.  Generate versioned multivariate episode dataset.
9.  Train simple anomaly/fault/forecasting baselines.
10. Evaluate on unseen episodes/scenarios.
11. Add physics consistency checks.
12. Build safety-agent orchestration.
13. Build dashboard + simulated human approval.
14. Validate claims before calling performance predictive/early-warning.

------------------------------------------------------------------------

## 29. Instructions to Another LLM Continuing This Project

-   Treat this file as the current consolidated project direction.
-   Do not reduce the idea to a P/T threshold detector.
-   Do not make alloy/material degradation a V1 requirement unless
    explicitly requested.
-   Do not assume the LLM performs numerical leak detection.
-   Preserve the distinction between experimental, simulation, and
    physics-generated data.
-   Prioritize physical credibility and scenario-level validation over
    headline accuracy.
-   Ask for engineering input when decisions depend on safety limits,
    physical parameters, or failure modes.
-   State assumptions/applicability when recommending equations or
    datasets.
-   Treat deployment as decision support, not a certified autonomous
    safety controller.
-   The main unresolved dependency is the engineering definition of the
    representative physical system.

------------------------------------------------------------------------

## 30. Architecture Summary

``` text
             COMPRESSED H₂ STORAGE SYSTEM
                        │
                        ▼
        ┌────────────────────────────────┐
        │ Pressure                       │
        │ Temperature                    │
        │ Inlet / outlet mass flow       │
        │ External H₂ concentration      │
        │ Valve / operating state        │
        └───────────────┬────────────────┘
                        │
                        ▼
               ┌────────────────┐
               │ Anomaly Model  │
               └───────┬────────┘
                       │
                       ▼
               ┌────────────────┐
               │ Fault / Leak   │
               │ Diagnosis      │
               └───────┬────────┘
                       │
                       ▼
               ┌────────────────┐
               │ Forecast Model │
               └───────┬────────┘
                       │
                       ▼
               ┌────────────────┐
               │ Physics Check  │
               │ / Digital Twin │
               └───────┬────────┘
                       │
                       ▼
        ┌────────────────────────────────┐
        │   PREDICTIVE SAFETY AGENT      │
        │ Observe → Correlate → Verify   │
        │ Assess → Explain → Recommend   │
        └───────────────┬────────────────┘
                        │
                        ▼
               OPERATOR / DASHBOARD
                        │
                 Human approval
                        │
                        ▼
            Simulated intervention
              in digital twin
```

------------------------------------------------------------------------

## 31. Current Status

The **concept, V1 scope, high-level architecture, data-construction
strategy, engineering handoff requirements, and responsibility split are
defined**.

The next critical dependency is the **engineering specification of the
representative compressed-hydrogen storage system**. Once that is fixed,
the digital twin and validated dataset can be constructed, followed by
the ML and agent layers.
