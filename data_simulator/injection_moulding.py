"""
Injection Moulding Machine Data Simulator 
- exposed on 4840 via OPC UA

FSM stages
1. PreInjection: Ramp melt_temp from 50 to 250 
2. Injection: Ramp injection_pressure from 500 to 2000 psi
3. Holding (Packing): Wait 3 seconds (fixed)
4. Cooling: Ramp melt_temp down until it drops to 50
5. Waiting (Idle): Wait 5 seconds (fixed)

We simulate 6 data points per reading:
  - melt_temp
  - injection_pressure
  - vibration_amplitude
  - vibration_frequency
  - stage
  - timestamp

Some sensor data ramps between states, some oscillate, and some remain constant.
- runs at 100Hz
- may want to add many more random data points but these 6 are the core.
"""

import time
import math
import random
from opcua import Server

# Create and start OPC UA server
server = Server()
server.set_endpoint("opc.tcp://0.0.0.0:4840/freeopcua/server/")
uri = "http://examples.freeopcua.github.io"
idx = server.register_namespace(uri)
objects = server.get_objects_node()
machine = objects.add_object(idx, "InjectionMouldingMachine")
melt_temp_var = machine.add_variable(idx, "MeltTemp", 0.0)
injection_pressure_var = machine.add_variable(idx, "InjectionPressure", 0.0)
vibration_amplitude_var = machine.add_variable(idx, "VibrationAmplitude", 0.0)
vibration_frequency_var = machine.add_variable(idx, "VibrationFrequency", 0.0)
stage_var = machine.add_variable(idx, "Stage", "")
timestamp_var = machine.add_variable(idx, "Timestamp", 0.0)
melt_temp_var.set_writable()
injection_pressure_var.set_writable()
vibration_amplitude_var.set_writable()
vibration_frequency_var.set_writable()
stage_var.set_writable()
timestamp_var.set_writable()
server.start()

SENSOR_RANGES = {
    "PreInjection": {
        "melt_temp": (50, 250), # ramp up from 50 to 250
        "injection_pressure": (0, 100), # idle
        "vibration_amplitude": (0.0, 0.5),
        "vibration_frequency": (5, 15)
    },
    "Injection": {
        "melt_temp": (220, 280), # keep around this range
        "injection_pressure": (500, 2000), # ramp up from 500 to 2000 psi
        "vibration_amplitude": (0.5, 2.0),
        "vibration_frequency": (40, 60)
    },
    "Holding": {
        "melt_temp": (220, 280),
        "injection_pressure": (300, 1000),
        "vibration_amplitude": (0.2, 1.0),
        "vibration_frequency": (20, 40)
    },
    "Cooling": {
        # ramp down the melt_temp from 100 to 50
        "melt_temp": (50, 100),
        "injection_pressure": (0, 100),
        "vibration_amplitude": (0.0, 0.5),
        "vibration_frequency": (5, 15)
    },
    "Waiting": {
        "melt_temp": (30, 40),
        "injection_pressure": (0, 50),
        "vibration_amplitude": (0.0, 0.2),
        "vibration_frequency": (5, 10)
    }
}

# the duration is randomized near to these times
STAGE_DURATIONS = {
    "PreInjection": 5,
    "Injection": 2,
    "Holding": 3, # exactly
    "Cooling": 5,
    "Waiting": 5 # exactly
}

# ML/predictive maintenance model info
machinePartFailureImminent = False
cycles_since_imminent = 0
cycles_to_failure = 0
CYCLES_TO_FAILURE_MIN = 2
CYCLES_TO_FAILURE_MAX = 8
IMMINENT_PROB_PER_CYCLE = 0.2 # 20% chance at start of each cycle

DRIFT_PERCENT = 0.15 # 15% drift in vibration amplitude if machine part failure is imminent

def simulate_ramped_sensor_value(value_range, current_time, stage_start, base_duration, ramp_direction, anomaly=False):
    """
    - base_duration: the typical duration of this state, randomized with +-20% of base
    - anomaly: if True, apply an exponential multiplier to simulate runaway
    - with gaussian noise (~5% of the range) 
    """
    # this randomizes the duration of the state
    effective_duration = random.uniform(0.8 * base_duration, 1.2 * base_duration)
    low, high = value_range
    elapsed = current_time - stage_start
    progress = min(max(elapsed / effective_duration, 0.0), 1.0) # clamp to [0, 1]

    # determine the amount of ramping/progress
    if ramp_direction == "up":
        base_value = low + progress * (high - low)
    elif ramp_direction == "down":
        base_value = high - progress * (high - low)
    elif ramp_direction == "constant": # no ramping
        base_value = (low + high) / 2.0
    else:
        base_value = low + progress * (high - low)

    if anomaly:
        # anomaly is exponential growth
        anomaly_factor = math.exp(elapsed / 2.0)
        base_value *= anomaly_factor

    noise = random.gauss(0, abs(high - low) * 0.05) # noise factor
    return base_value + noise

def simulate_periodic_sensor_value(value_range, current_time, stage_start, period=2.0, anomaly=False):
    """
    This is for sensor that is a sine wave, with same exponential anomaly as the normal ramp
    """
    # this randomizes the duration of the state
    low, high = value_range
    amplitude = (high - low) / 2.0
    offset = (high + low) / 2.0
    elapsed = current_time - stage_start
    pattern = math.sin(2 * math.pi * elapsed / period) # oscillate between -1 and 1
    base_value = offset + amplitude * pattern

    if anomaly:
        anomaly_factor = math.exp(elapsed / 2.0)
        base_value *= anomaly_factor

    noise = random.gauss(0, abs(high - low) * 0.05)
    return base_value + noise

def run_preinjection():
    """
    - Ramp melt_temp from 50 to 250 (noisy and variable)
    - Transition when melt_temp >= 250
    - Other sensors run as constant/noisy
    - 10% chance an anomaly is applied to vibration_amplitude
    """
    global machinePartFailureImminent
    state = "PreInjection"
    base_duration = STAGE_DURATIONS[state]
    stage_start = time.time()
    anomaly_vib = (random.random() < 0.1)
    while True:
        current_time = time.time()
        # ramp melt_temp upward 
        melt_temp = simulate_ramped_sensor_value(SENSOR_RANGES[state]["melt_temp"], current_time, stage_start, base_duration, "up")
        # other sensors are constant
        injection_pressure = simulate_ramped_sensor_value(SENSOR_RANGES[state]["injection_pressure"], current_time, stage_start, base_duration, "constant")
        vibration_amplitude = simulate_ramped_sensor_value(SENSOR_RANGES[state]["vibration_amplitude"], current_time, stage_start, base_duration, "constant", anomaly=anomaly_vib)
        if machinePartFailureImminent:
            drift = 1 + DRIFT_PERCENT * ((current_time - stage_start) / base_duration)
            vibration_amplitude *= drift
        vibration_frequency = simulate_periodic_sensor_value(SENSOR_RANGES[state]["vibration_frequency"], current_time, stage_start, period=2.0)
        reading = {
            "timestamp": current_time,
            "stage": state,
            "melt_temp": melt_temp,
            "injection_pressure": injection_pressure,
            "vibration_amplitude": vibration_amplitude,
            "vibration_frequency": vibration_frequency
        }
        # update opc ua
        melt_temp_var.set_value(melt_temp)
        injection_pressure_var.set_value(injection_pressure)
        vibration_amplitude_var.set_value(vibration_amplitude)
        vibration_frequency_var.set_value(vibration_frequency)
        stage_var.set_value(state)
        timestamp_var.set_value(current_time)
        # transition when melt_temp reaches or exceeds 250
        if melt_temp >= 250:
            print(f"Transitioning from {state} after {current_time - stage_start:.2f} s (melt_temp={melt_temp:.2f}°C).")
            break
        time.sleep(0.01)  # 100Hz
    # print(f"Exiting {state} state.")

def run_injection():
    """
    - ramp injection_pressure from 500 to 2000 psi
    - transition when injection_pressure >= 2000 psi
    - other sensors behave constant/oscillatory
    - 10% chance an anomaly is applied to injection_pressure
    """
    global machinePartFailureImminent
    state = "Injection"
    base_duration = STAGE_DURATIONS[state]
    stage_start = time.time()
    anomaly_inj = (random.random() < 0.1)
    while True:
        current_time = time.time()
        melt_temp = simulate_ramped_sensor_value(SENSOR_RANGES[state]["melt_temp"], current_time, stage_start, base_duration, "constant")
        # ramp injection_pressure upward
        injection_pressure = simulate_ramped_sensor_value(SENSOR_RANGES[state]["injection_pressure"], current_time, stage_start, base_duration, "up", anomaly=anomaly_inj)
        vibration_amplitude = simulate_ramped_sensor_value(SENSOR_RANGES[state]["vibration_amplitude"], current_time, stage_start, base_duration, "constant")
        if machinePartFailureImminent:
            drift = 1 + DRIFT_PERCENT * ((current_time - stage_start) / base_duration)
            vibration_amplitude *= drift
        vibration_frequency = simulate_periodic_sensor_value(SENSOR_RANGES[state]["vibration_frequency"], current_time, stage_start, period=2.0)
        reading = {
            "timestamp": current_time,
            "stage": state,
            "melt_temp": melt_temp,
            "injection_pressure": injection_pressure,
            "vibration_amplitude": vibration_amplitude,
            "vibration_frequency": vibration_frequency
        }
        melt_temp_var.set_value(melt_temp)
        injection_pressure_var.set_value(injection_pressure)
        vibration_amplitude_var.set_value(vibration_amplitude)
        vibration_frequency_var.set_value(vibration_frequency)
        stage_var.set_value(state)
        timestamp_var.set_value(current_time)
        if injection_pressure >= 2000:
            print(f"Transitioning from {state} after {current_time - stage_start:.2f} s (injection_pressure={injection_pressure:.2f} psi).")
            break
        time.sleep(0.01)
    # print(f"Exiting {state} state.")

def run_holding():
    """
    - Fixed to 3 seconds
    - Sensor values constant
    - 10% chance an anomaly is applied to vibration_amplitude
    """
    global machinePartFailureImminent
    state = "Holding"
    duration = STAGE_DURATIONS[state]
    stage_start = time.time()
    anomaly_hold = (random.random() < 0.1)
    while time.time() - stage_start < duration:
        current_time = time.time()
        melt_temp = simulate_ramped_sensor_value(SENSOR_RANGES[state]["melt_temp"], current_time, stage_start, duration, "constant")
        injection_pressure = simulate_ramped_sensor_value(SENSOR_RANGES[state]["injection_pressure"], current_time, stage_start, duration, "constant")
        vibration_amplitude = simulate_ramped_sensor_value(SENSOR_RANGES[state]["vibration_amplitude"], current_time, stage_start, duration, "constant", anomaly=anomaly_hold)
        if machinePartFailureImminent:
            drift = 1 + DRIFT_PERCENT * ((current_time - stage_start) / duration)
            vibration_amplitude *= drift
        vibration_frequency = simulate_periodic_sensor_value(SENSOR_RANGES[state]["vibration_frequency"], current_time, stage_start, period=2.0)
        reading = {
            "timestamp": current_time,
            "stage": state,
            "melt_temp": melt_temp,
            "injection_pressure": injection_pressure,
            "vibration_amplitude": vibration_amplitude,
            "vibration_frequency": vibration_frequency
        }
        melt_temp_var.set_value(melt_temp)
        injection_pressure_var.set_value(injection_pressure)
        vibration_amplitude_var.set_value(vibration_amplitude)
        vibration_frequency_var.set_value(vibration_frequency)
        stage_var.set_value(state)
        timestamp_var.set_value(current_time)
        time.sleep(0.01)
    print(f"Exiting {state} state after {time.time() - stage_start:.2f} s.")

def run_cooling():
    """
    - ramp melt_temp down from 100 to 50
    - transition when melt_temp <= 50
    - 10% chance an anomaly is applied to melt_temp
    """
    global machinePartFailureImminent
    state = "Cooling"
    base_duration = STAGE_DURATIONS[state]
    effective_duration = random.uniform(0.8 * base_duration, 1.2 * base_duration) # some variation for fun

    orig_uniform = random.uniform
    random.uniform = lambda a, b: effective_duration # stupid fix to resolve sim getting stuck in cooling state

    stage_start = time.time()
    anomaly_cool = (random.random() < 0.1)
    while True:
        current_time = time.time()
        # elapsed = current_time - stage_start
        melt_temp = simulate_ramped_sensor_value(SENSOR_RANGES[state]["melt_temp"], current_time, stage_start, effective_duration, "down")
        injection_pressure = simulate_ramped_sensor_value(SENSOR_RANGES[state]["injection_pressure"],current_time, stage_start, effective_duration,"constant")
        vibration_amplitude = simulate_ramped_sensor_value(SENSOR_RANGES[state]["vibration_amplitude"],current_time, stage_start, effective_duration, "constant")
        if machinePartFailureImminent:
            drift = 1 + DRIFT_PERCENT * ((current_time - stage_start) / effective_duration)
            vibration_amplitude *= drift
        vibration_frequency = simulate_periodic_sensor_value(SENSOR_RANGES[state]["vibration_frequency"],current_time, stage_start, period=2.0)
        reading = {
            "timestamp": current_time,
            "stage": state,
            "melt_temp": melt_temp,
            "injection_pressure": injection_pressure,
            "vibration_amplitude": vibration_amplitude,
            "vibration_frequency": vibration_frequency
        }
        melt_temp_var.set_value(melt_temp)
        injection_pressure_var.set_value(injection_pressure)
        vibration_amplitude_var.set_value(vibration_amplitude)
        vibration_frequency_var.set_value(vibration_frequency)
        stage_var.set_value(state)
        timestamp_var.set_value(current_time)
        if melt_temp <= 50:
            print(f"Transitioning from {state} after {effective_duration:.2f} s (melt_temp={melt_temp:.2f}°C).")
            break
        time.sleep(0.01)
    random.uniform = orig_uniform
    # print(f"Exiting {state} state.")

def run_waiting():
    """
    - fixed to 30 seconds
    - sensor values constant
    """
    global machinePartFailureImminent
    state = "Waiting"
    duration = STAGE_DURATIONS[state]
    stage_start = time.time()
    while time.time() - stage_start < duration:
        current_time = time.time()
        melt_temp = simulate_ramped_sensor_value(SENSOR_RANGES[state]["melt_temp"], current_time, stage_start, duration, "constant")
        injection_pressure = simulate_ramped_sensor_value(SENSOR_RANGES[state]["injection_pressure"], current_time, stage_start, duration, "constant")
        vibration_amplitude = simulate_ramped_sensor_value(SENSOR_RANGES[state]["vibration_amplitude"], current_time, stage_start, duration, "constant")
        if machinePartFailureImminent:
            drift = 1 + DRIFT_PERCENT * ((current_time - stage_start) / duration)
            vibration_amplitude *= drift
        vibration_frequency = simulate_periodic_sensor_value(SENSOR_RANGES[state]["vibration_frequency"], current_time, stage_start, period=2.0)
        reading = {
            "timestamp": current_time,
            "stage": state,
            "melt_temp": melt_temp,
            "injection_pressure": injection_pressure,
            "vibration_amplitude": vibration_amplitude,
            "vibration_frequency": vibration_frequency
        }
        melt_temp_var.set_value(melt_temp)
        injection_pressure_var.set_value(injection_pressure)
        vibration_amplitude_var.set_value(vibration_amplitude)
        vibration_frequency_var.set_value(vibration_frequency)
        stage_var.set_value(state)
        timestamp_var.set_value(current_time)
        time.sleep(0.01)
    print(f"Exiting {state} state after {time.time() - stage_start:.2f} s.")

def run_cycle():
    """
    PreInjection -> Injection -> Holding -> Cooling -> Waiting.
    """
    cycle_data = []
    for fn in (run_preinjection, run_injection, run_holding, run_cooling, run_waiting):
        fn() # run each cycle
    return cycle_data

def main():
    global machinePartFailureImminent, cycles_since_imminent, cycles_to_failure

    try:
        while True:
            print("=== Starting new cycle ===")

            # At beginning of each cycle, we check if a failure is imminent
            if not machinePartFailureImminent and random.random() < IMMINENT_PROB_PER_CYCLE:
                machinePartFailureImminent = True
                cycles_since_imminent = 0
                cycles_to_failure = 0
                # choose a random failure span
                cycles_to_failure = random.randint(CYCLES_TO_FAILURE_MIN, CYCLES_TO_FAILURE_MAX)
                print(f"Part failure imminent — in {cycles_to_failure} cycles. this data not provided to ML model.")

            # run a full cycle
            cycle_data = run_cycle()

            # label and plan to trigger actual failure
            if machinePartFailureImminent:
                cycles_since_imminent += 1 # track since imminent flag went high
                
                # trigger failure after a certain number of cycles (defined randomly in a range)
                if cycles_since_imminent >= cycles_to_failure:
                    print("Part has failed—stopping for replacement")

                    # the stage is PartReplacement since the part is broken
                    # this is used by the ML model to predict this stage happening
                    stage_var.set_value("PartReplacement")
                    melt_temp_var.set_value(0.0)
                    injection_pressure_var.set_value(0.0)
                    vibration_amplitude_var.set_value(0.0)
                    vibration_frequency_var.set_value(0.0)
                    timestamp_var.set_value(time.time())
                    time.sleep(10)
                    stage_var.set_value("PreInjection") # set back to restart
                    machinePartFailureImminent = False
                    cycles_since_imminent = 0
                    cycles_to_failure = 0


    except KeyboardInterrupt:
        print("exiting")
    finally:
        server.stop() #stop opcua server

if __name__ == "__main__":
    main()
