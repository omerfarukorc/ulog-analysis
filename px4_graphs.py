"""
PX4 Flight Review - Standard Graph Generator
Exact replica of https://review.px4.io graph order and data selections.
Optimized: SVG rendering + LTTB downsampling for Dash/Plotly.
"""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pyulog import ULog
try:
    from scipy.signal import welch
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

# ============================================================
# Theme
# ============================================================
COLORS = {
    'bg': '#0a0f1a',
    'panel': '#111827',
    'grid': '#1f2937',
    'text': '#9ca3af',
    'accent': '#3b82f6',
}
TRACE_COLORS = [
    '#6366f1', '#10b981', '#f59e0b', '#ef4444',
    '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16',
    '#f97316', '#14b8a6', '#a855f7', '#fb7185',
]

MAX_POINTS = 2000
GRAPH_HEIGHT = 500  # match dcc.Graph container height

def _base_layout(title, yaxis_title='', height=GRAPH_HEIGHT):
    return dict(
        template='plotly_dark',
        paper_bgcolor=COLORS['panel'],
        plot_bgcolor=COLORS['bg'],
        hovermode='x unified',
        height=height,
        margin=dict(l=55, r=15, t=35, b=40),
        title=dict(text=title, font=dict(size=13, color='#e5e7eb'), x=0.01, y=0.97),
        xaxis=dict(title='Time (s)', gridcolor=COLORS['grid'], zeroline=False),
        yaxis=dict(title=yaxis_title, gridcolor=COLORS['grid'], zeroline=False),
        legend=dict(orientation='h', y=1.08, font=dict(size=9)),
        showlegend=True,
    )

# ============================================================
# Helpers
# ============================================================

def _downsample(x, y, max_pts=MAX_POINTS):
    """Downsample keeping max-deviation point per bucket."""
    n = len(x)
    if n <= max_pts:
        return x, y
    step = n / max_pts
    indices = [0]
    for i in range(1, max_pts - 1):
        start = int(i * step)
        end = min(int((i + 1) * step), n)
        if start >= end:
            indices.append(start)
            continue
        bucket = y[start:end]
        avg_val = np.mean(bucket)
        best = start + np.argmax(np.abs(bucket - avg_val))
        indices.append(best)
    indices.append(n - 1)
    indices = np.array(indices)
    return x[indices], y[indices]

def _find_topic(ulog, name, multi_id=0):
    for d in ulog.data_list:
        if d.name == name and d.multi_id == multi_id:
            return d
    for d in ulog.data_list:
        if d.name == name:
            return d
    return None

def _get_time(data_obj):
    return data_obj.data['timestamp'] / 1e6

def _add_trace(fig, x, y, name, color, width=1.5, dash=None, secondary_y=None, mode='lines'):
    """Add a downsampled SVG Scatter trace."""
    xd, yd = _downsample(np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64))
    trace = go.Scatter(x=xd, y=yd, name=name, mode=mode,
                       line=dict(color=color, width=width, dash=dash))
    if secondary_y is not None:
        fig.add_trace(trace, secondary_y=secondary_y)
    else:
        fig.add_trace(trace)

def quat_to_euler(q0, q1, q2, q3):
    """Quaternion to Euler angles (roll, pitch, yaw) in degrees."""
    sinr_cosp = 2.0 * (q0 * q1 + q2 * q3)
    cosr_cosp = 1.0 - 2.0 * (q1 * q1 + q2 * q2)
    roll = np.arctan2(sinr_cosp, cosr_cosp)
    sinp = np.clip(2.0 * (q0 * q2 - q3 * q1), -1.0, 1.0)
    pitch = np.arcsin(sinp)
    siny_cosp = 2.0 * (q0 * q3 + q1 * q2)
    cosy_cosp = 1.0 - 2.0 * (q2 * q2 + q3 * q3)
    yaw = np.arctan2(siny_cosp, cosy_cosp)
    return np.degrees(roll), np.degrees(pitch), np.degrees(yaw)

def get_available_topics(ulog):
    return set(d.name for d in ulog.data_list)


# ============================================================
# Vehicle Info Extraction
# ============================================================

def get_vehicle_info(ulog):
    info = {}
    msg = ulog.msg_info_dict

    info['sys_name'] = msg.get('sys_name', 'N/A')
    info['ver_hw'] = msg.get('ver_hw', 'N/A')
    info['ver_sw'] = msg.get('ver_sw', 'N/A')
    info['ver_sw_branch'] = msg.get('ver_sw_branch', 'N/A')

    if 'ver_sw_release' in msg:
        v = msg['ver_sw_release']
        if isinstance(v, int):
            info['ver_sw_release'] = f"v{(v >> 24) & 0xFF}.{(v >> 16) & 0xFF}.{(v >> 8) & 0xFF}"
        else:
            info['ver_sw_release'] = str(v)
    else:
        info['ver_sw_release'] = 'N/A'

    info['ver_os'] = msg.get('ver_os_name', 'N/A')
    ver_os_v = msg.get('ver_os_release', '')
    if isinstance(ver_os_v, int):
        info['ver_os_version'] = f"v{(ver_os_v >> 24) & 0xFF}.{(ver_os_v >> 16) & 0xFF}.{(ver_os_v >> 8) & 0xFF}"
    else:
        info['ver_os_version'] = str(ver_os_v) if ver_os_v else ''

    start_us = ulog.start_timestamp
    last_us = ulog.last_timestamp
    duration_s = (last_us - start_us) / 1e6
    info['duration'] = f"{int(duration_s // 60)}:{int(duration_s % 60):02d}"
    info['duration_s'] = duration_s

    try:
        import datetime
        utc_offset = msg.get('time_ref_utc', 0)
        if utc_offset > 0:
            info['start_time'] = datetime.datetime.utcfromtimestamp(utc_offset / 1e6).strftime('%d-%m-%Y %H:%M')
        else:
            info['start_time'] = 'N/A'
    except:
        info['start_time'] = 'N/A'

    info['uuid'] = msg.get('sys_uuid', 'N/A')
    topics = get_available_topics(ulog)
    info['estimator'] = 'EKF2' if ('estimator_status' in topics or 'estimator_states' in topics) else 'LPE/Other'

    try:
        _compute_flight_stats(ulog, info)
    except:
        pass

    return info


def _compute_flight_stats(ulog, info):
    lp = _find_topic(ulog, 'vehicle_local_position')
    if lp is None:
        return
    t = _get_time(lp)
    x = lp.data.get('x', np.zeros_like(t))
    y = lp.data.get('y', np.zeros_like(t))
    z = lp.data.get('z', np.zeros_like(t))
    vx = lp.data.get('vx', np.zeros_like(t))
    vy = lp.data.get('vy', np.zeros_like(t))
    vz = lp.data.get('vz', np.zeros_like(t))

    dx, dy = np.diff(x), np.diff(y)
    info['distance'] = f"{np.sum(np.sqrt(dx**2 + dy**2)):.1f} m"
    info['max_alt'] = f"{-np.min(z):.1f} m"
    h_speed = np.sqrt(vx**2 + vy**2)
    info['max_speed'] = f"{np.max(h_speed) * 3.6:.1f} km/h"
    info['avg_speed'] = f"{np.mean(h_speed) * 3.6:.1f} km/h"
    info['max_speed_up'] = f"{-np.min(vz) * 3.6:.1f} km/h"
    info['max_speed_down'] = f"{np.max(vz) * 3.6:.1f} km/h"

    att = _find_topic(ulog, 'vehicle_attitude')
    if att and 'q[0]' in att.data:
        roll, pitch, _ = quat_to_euler(
            att.data['q[0]'], att.data['q[1]'],
            att.data['q[2]'], att.data['q[3]']
        )
        info['max_tilt'] = f"{np.max(np.sqrt(roll**2 + pitch**2)):.1f} deg"


# ============================================================
# PX4 Flight Review Standard Graphs
# Exact order and data matching https://review.px4.io
# ============================================================

# 1. Altitude Estimate
def graph_altitude(ulog):
    """Altitude: GPS Alt (MSL), Barometer, Fused Estimate, Altitude Setpoint"""
    gp = _find_topic(ulog, 'vehicle_gps_position')
    gpos = _find_topic(ulog, 'vehicle_global_position')
    lp = _find_topic(ulog, 'vehicle_local_position')
    air = _find_topic(ulog, 'vehicle_air_data')
    if air is None and lp is None and gp is None:
        return None

    fig = go.Figure()

    # GPS Altitude (MSL)
    if gp is not None:
        t = _get_time(gp)
        if 'altitude_msl_m' in gp.data:
            _add_trace(fig, t, gp.data['altitude_msl_m'], 'GPS Altitude (MSL)', TRACE_COLORS[0])
        elif 'alt' in gp.data:
            _add_trace(fig, t, gp.data['alt'] * 0.001 if np.max(gp.data['alt']) > 10000 else gp.data['alt'],
                       'GPS Altitude (MSL)', TRACE_COLORS[0])

    # Barometer Altitude
    if air is not None and 'baro_alt_meter' in air.data:
        t2 = _get_time(air)
        _add_trace(fig, t2, air.data['baro_alt_meter'], 'Barometer Altitude', TRACE_COLORS[1], width=1)

    # Fused Altitude Estimation
    if gpos is not None and 'alt' in gpos.data:
        t3 = _get_time(gpos)
        _add_trace(fig, t3, gpos.data['alt'], 'Fused Altitude Estimation', TRACE_COLORS[2], width=1)

    # Altitude Setpoint (from position_setpoint_triplet or local_position_setpoint)
    pst = _find_topic(ulog, 'position_setpoint_triplet')
    if pst is not None and 'current.alt' in pst.data:
        t4 = _get_time(pst)
        _add_trace(fig, t4, pst.data['current.alt'], 'Altitude Setpoint',
                   '#ec4899', width=1.5, dash='dash', mode='lines')
    else:
        lp_sp = _find_topic(ulog, 'vehicle_local_position_setpoint')
        if lp_sp is not None and 'z' in lp_sp.data and gpos is not None and 'alt' in gpos.data:
            t4 = _get_time(lp_sp)
            # Convert local z setpoint to approximate MSL altitude
            ref_alt = gpos.data['alt'][0] if len(gpos.data['alt']) > 0 else 0
            _add_trace(fig, t4, ref_alt - lp_sp.data['z'], 'Altitude Setpoint',
                       '#ec4899', width=1.5, dash='dash', mode='lines')

    fig.update_layout(**_base_layout('Altitude Estimate', '[m]'))
    return fig


# 2-4. Roll/Pitch/Yaw Angle
def _attitude_graph(ulog, axis_name, axis_idx):
    """Attitude angle: Estimated + Setpoint"""
    att = _find_topic(ulog, 'vehicle_attitude')
    if att is None or 'q[0]' not in att.data:
        return None

    fig = go.Figure()
    t = _get_time(att)
    roll, pitch, yaw = quat_to_euler(
        att.data['q[0]'], att.data['q[1]'],
        att.data['q[2]'], att.data['q[3]']
    )
    angles = [roll, pitch, yaw]
    _add_trace(fig, t, angles[axis_idx], f'{axis_name} Estimated', TRACE_COLORS[0])

    # Setpoint
    sp = _find_topic(ulog, 'vehicle_attitude_setpoint')
    if sp:
        t2 = _get_time(sp)
        sp_fields = ['roll_d', 'pitch_d', 'yaw_d']
        # Try new field names first, then old
        for field_set in [sp_fields, ['roll_body', 'pitch_body', 'yaw_body']]:
            if field_set[axis_idx] in sp.data:
                _add_trace(fig, t2, np.degrees(sp.data[field_set[axis_idx]]),
                           f'{axis_name} Setpoint', TRACE_COLORS[1], width=1, dash='dash')
                break

    fig.update_layout(**_base_layout(f'{axis_name} Angle', '[deg]'))
    return fig

def graph_roll(ulog): return _attitude_graph(ulog, 'Roll', 0)
def graph_pitch(ulog): return _attitude_graph(ulog, 'Pitch', 1)
def graph_yaw(ulog): return _attitude_graph(ulog, 'Yaw', 2)


# 5-7. Roll/Pitch/Yaw Angular Rate
def _rate_graph(ulog, axis_name, axis_idx):
    """Angular rate: Estimated + Setpoint + Rate Integral"""
    av = _find_topic(ulog, 'vehicle_angular_velocity')
    if av is None:
        return None

    fig = go.Figure()
    t = _get_time(av)
    field = f'xyz[{axis_idx}]'
    if field in av.data:
        _add_trace(fig, t, np.degrees(av.data[field]), f'{axis_name} Rate Estimated', TRACE_COLORS[0])

    # Rate setpoint
    rs = _find_topic(ulog, 'vehicle_rates_setpoint')
    if rs:
        t2 = _get_time(rs)
        sp_fields = ['roll', 'pitch', 'yaw']
        if sp_fields[axis_idx] in rs.data:
            _add_trace(fig, t2, np.degrees(rs.data[sp_fields[axis_idx]]),
                       f'{axis_name} Rate Setpoint', TRACE_COLORS[1], width=1, dash='dash')

    # Rate integral
    ri = _find_topic(ulog, 'rate_ctrl_status')
    if ri:
        t3 = _get_time(ri)
        ri_fields = ['rollspeed_integ', 'pitchspeed_integ', 'yawspeed_integ']
        if ri_fields[axis_idx] in ri.data:
            _add_trace(fig, t3, ri.data[ri_fields[axis_idx]] * 100,
                       f'{axis_name} Rate Integral (*100)', TRACE_COLORS[2], width=1)

    fig.update_layout(**_base_layout(f'{axis_name} Angular Rate', '[deg/s]'))
    return fig

def graph_roll_rate(ulog): return _rate_graph(ulog, 'Roll', 0)
def graph_pitch_rate(ulog): return _rate_graph(ulog, 'Pitch', 1)
def graph_yaw_rate(ulog): return _rate_graph(ulog, 'Yaw', 2)


# 8-10. Local Position X/Y/Z
def _local_pos_graph(ulog, axis, label):
    """Local position: Estimated + Setpoint"""
    lp = _find_topic(ulog, 'vehicle_local_position')
    if lp is None:
        return None

    fig = go.Figure()
    t = _get_time(lp)
    if axis in lp.data:
        _add_trace(fig, t, lp.data[axis], f'{label} Estimated', TRACE_COLORS[0])

    sp = _find_topic(ulog, 'vehicle_local_position_setpoint')
    if sp and axis in sp.data:
        t2 = _get_time(sp)
        _add_trace(fig, t2, sp.data[axis], f'{label} Setpoint', TRACE_COLORS[1], width=1, dash='dash')

    fig.update_layout(**_base_layout(f'Local Position {label}', '[m]'))
    return fig

def graph_local_pos_x(ulog): return _local_pos_graph(ulog, 'x', 'X')
def graph_local_pos_y(ulog): return _local_pos_graph(ulog, 'y', 'Y')
def graph_local_pos_z(ulog): return _local_pos_graph(ulog, 'z', 'Z')


# 11. Velocity (all axes on one graph)
def graph_velocity(ulog):
    """Velocity: X/Y/Z Estimated + Setpoints"""
    lp = _find_topic(ulog, 'vehicle_local_position')
    if lp is None:
        return None
    fig = go.Figure()
    t = _get_time(lp)

    vel_colors = [TRACE_COLORS[0], TRACE_COLORS[1], TRACE_COLORS[2]]
    sp_colors = [TRACE_COLORS[5], TRACE_COLORS[4], TRACE_COLORS[6]]

    for i, (field, label) in enumerate([('vx', 'X'), ('vy', 'Y'), ('vz', 'Z')]):
        if field in lp.data:
            _add_trace(fig, t, lp.data[field], label, vel_colors[i])

    sp = _find_topic(ulog, 'vehicle_local_position_setpoint')
    if sp:
        t2 = _get_time(sp)
        for i, (field, label) in enumerate([('vx', 'X Setpoint'), ('vy', 'Y Setpoint'), ('vz', 'Z Setpoint')]):
            if field in sp.data:
                _add_trace(fig, t2, sp.data[field], label, sp_colors[i], width=1, dash='dash')

    fig.update_layout(**_base_layout('Velocity', '[m/s]'))
    return fig


# 12. Manual Control Inputs
def graph_manual_control(ulog):
    """Manual Control Inputs (Radio or Joystick)"""
    mc = _find_topic(ulog, 'manual_control_setpoint')
    if mc is None:
        return None
    fig = go.Figure()
    t = _get_time(mc)

    # Try new field names first, then old ones
    new_fields = [('roll', 'Y / Roll'), ('pitch', 'X / Pitch'), ('yaw', 'Yaw'), ('throttle', 'Throttle')]
    old_fields = [('y', 'Y / Roll'), ('x', 'X / Pitch'), ('r', 'Yaw'), ('z', 'Throttle')]

    fields_to_use = new_fields if 'roll' in mc.data else old_fields
    for i, (field, name) in enumerate(fields_to_use):
        if field in mc.data:
            _add_trace(fig, t, mc.data[field], name, TRACE_COLORS[i])

    # Aux channels
    for aux_field, aux_name in [('aux1', 'Aux1'), ('aux2', 'Aux2')]:
        if aux_field in mc.data:
            _add_trace(fig, t, mc.data[aux_field], aux_name, TRACE_COLORS[4 + (0 if aux_field == 'aux1' else 1)], width=1)

    layout = _base_layout('Manual Control Inputs (Radio or Joystick)', '')
    layout['yaxis']['range'] = [-1.1, 1.1]
    fig.update_layout(**layout)
    return fig


# 13. Actuator Controls (torque + thrust)
def graph_actuator_controls(ulog):
    """Actuator Controls: Roll/Pitch/Yaw torque + Thrust"""
    # Try new dynamic allocation topics first
    motors = _find_topic(ulog, 'actuator_motors')
    if motors is not None:
        fig = go.Figure()
        t = _get_time(motors)
        for i in range(12):
            f = f'control[{i}]'
            if f in motors.data:
                vals = motors.data[f]
                if not np.isnan(vals).all() and np.any(vals != 0):
                    _add_trace(fig, t, vals, f'Motor {i+1}', TRACE_COLORS[i % len(TRACE_COLORS)], width=1)
        fig.update_layout(**_base_layout('Motor Outputs', ''))
        return fig

    # Fallback: old actuator_controls_0
    act = _find_topic(ulog, 'actuator_controls_0')
    if act is None:
        return None
    fig = go.Figure()
    t = _get_time(act)
    for i, (field, label) in enumerate([('control[0]', 'Roll'), ('control[1]', 'Pitch'),
                                         ('control[2]', 'Yaw'), ('control[3]', 'Thrust')]):
        if field in act.data:
            _add_trace(fig, t, act.data[field], label, TRACE_COLORS[i])

    fig.update_layout(**_base_layout('Actuator Controls', ''))
    return fig


# 14. Actuator Outputs
def graph_actuator_outputs(ulog):
    """Actuator Outputs (PWM)"""
    act = _find_topic(ulog, 'actuator_outputs')
    if act is None:
        return None
    fig = go.Figure()
    t = _get_time(act)
    num_outputs = int(np.max(act.data.get('noutputs', [16]))) if 'noutputs' in act.data else 16
    num_outputs = min(num_outputs, 16)
    for i in range(num_outputs):
        field = f'output[{i}]'
        if field in act.data:
            vals = act.data[field]
            if not np.all(vals == vals[0]):  # skip constant outputs
                _add_trace(fig, t, vals, f'Output {i}', TRACE_COLORS[i % len(TRACE_COLORS)], width=1)
    fig.update_layout(**_base_layout('Actuator Outputs (Main)', ''))
    return fig


# 15. Raw Acceleration
def graph_raw_accel(ulog):
    """Raw Acceleration: X/Y/Z"""
    sc = _find_topic(ulog, 'sensor_combined')
    if sc is None:
        return None
    fig = go.Figure()
    t = _get_time(sc)
    fields = [('accelerometer_m_s2[0]', 'X'), ('accelerometer_m_s2[1]', 'Y'), ('accelerometer_m_s2[2]', 'Z')]
    for i, (f, label) in enumerate(fields):
        if f in sc.data:
            _add_trace(fig, t, sc.data[f], label, TRACE_COLORS[i], width=1)
    fig.update_layout(**_base_layout('Raw Acceleration', '[m/s²]'))
    return fig


# 16. Vibration Metrics
def graph_vibration(ulog):
    """Vibration Metrics: accel vibration level per IMU"""
    imu = _find_topic(ulog, 'vehicle_imu_status', 0)
    if imu is not None and 'accel_vibration_metric' in imu.data:
        fig = go.Figure()
        t = _get_time(imu)
        _add_trace(fig, t, imu.data['accel_vibration_metric'], 'Accel 0 Vibration [m/s²]', TRACE_COLORS[0])

        # Try additional IMUs
        for inst in range(1, 4):
            imu_n = _find_topic(ulog, 'vehicle_imu_status', inst)
            if imu_n is not None and 'accel_vibration_metric' in imu_n.data:
                t_n = _get_time(imu_n)
                _add_trace(fig, t_n, imu_n.data['accel_vibration_metric'],
                           f'Accel {inst} Vibration [m/s²]', TRACE_COLORS[inst])

        fig.update_layout(**_base_layout('Vibration Metrics', '[m/s²]'))
        return fig

    # Fallback: estimator vibe
    est = _find_topic(ulog, 'estimator_status')
    if est and 'vibe[0]' in est.data:
        fig = go.Figure()
        t = _get_time(est)
        for i in range(3):
            f = f'vibe[{i}]'
            if f in est.data:
                _add_trace(fig, t, est.data[f], f'Vibe {"XYZ"[i]}', TRACE_COLORS[i], width=1)
        fig.update_layout(**_base_layout('Vibration Metrics', '[m/s²]'))
        return fig

    return None


# 17. Raw Angular Speed (Gyroscope)
def graph_raw_gyro(ulog):
    """Raw Angular Speed: X/Y/Z in deg/s"""
    sc = _find_topic(ulog, 'sensor_combined')
    if sc is None:
        return None
    fig = go.Figure()
    t = _get_time(sc)
    fields = [('gyro_rad[0]', 'X'), ('gyro_rad[1]', 'Y'), ('gyro_rad[2]', 'Z')]
    for i, (f, label) in enumerate(fields):
        if f in sc.data:
            _add_trace(fig, t, np.degrees(sc.data[f]), label, TRACE_COLORS[i], width=1)
    fig.update_layout(**_base_layout('Raw Angular Speed (Gyroscope)', '[deg/s]'))
    return fig


# 18. Raw Magnetic Field Strength
def graph_magnetometer(ulog):
    """Raw Magnetic Field: X/Y/Z"""
    mag = _find_topic(ulog, 'vehicle_magnetometer')
    ga_topic = 'vehicle_magnetometer'
    if mag is None:
        mag = _find_topic(ulog, 'sensor_combined')
        ga_topic = 'sensor_combined'
    if mag is None:
        return None
    fig = go.Figure()
    t = _get_time(mag)

    if ga_topic == 'vehicle_magnetometer':
        fields = [('magnetometer_ga[0]', 'X'), ('magnetometer_ga[1]', 'Y'), ('magnetometer_ga[2]', 'Z')]
    else:
        fields = [('magnetometer_ga[0]', 'X'), ('magnetometer_ga[1]', 'Y'), ('magnetometer_ga[2]', 'Z')]

    for i, (f, label) in enumerate(fields):
        if f in mag.data:
            _add_trace(fig, t, mag.data[f], label, TRACE_COLORS[i], width=1)

    fig.update_layout(**_base_layout('Raw Magnetic Field Strength', '[gauss]'))
    return fig


# 19. Distance Sensor
def graph_distance_sensor(ulog):
    """Distance Sensor + estimated dist_bottom"""
    ds = _find_topic(ulog, 'distance_sensor')
    lp = _find_topic(ulog, 'vehicle_local_position')
    if ds is None and lp is None:
        return None
    fig = go.Figure()

    if ds is not None and 'current_distance' in ds.data:
        t = _get_time(ds)
        _add_trace(fig, t, ds.data['current_distance'], 'Distance', TRACE_COLORS[0])

    if lp is not None and 'dist_bottom' in lp.data:
        t2 = _get_time(lp)
        _add_trace(fig, t2, lp.data['dist_bottom'], 'Estimated Distance Bottom [m]', TRACE_COLORS[2], width=1)

    fig.update_layout(**_base_layout('Distance Sensor', '[m]'))
    return fig


# 20. GPS Uncertainty
def graph_gps_uncertainty(ulog):
    """GPS: eph, epv, hdop, vdop, speed acc, satellites, fix type"""
    gps = _find_topic(ulog, 'vehicle_gps_position')
    if gps is None:
        gps = _find_topic(ulog, 'sensor_gps')
    if gps is None:
        return None
    fig = go.Figure()
    t = _get_time(gps)

    fields = [
        ('eph', 'Horizontal position accuracy [m]'),
        ('epv', 'Vertical position accuracy [m]'),
        ('hdop', 'Horizontal dilution of precision [m]'),
        ('vdop', 'Vertical dilution of precision [m]'),
        ('s_variance_m_s', 'Speed accuracy [m/s]'),
        ('satellites_used', 'Num Satellites used'),
        ('fix_type', 'GPS Fix'),
    ]
    for i, (f, label) in enumerate(fields):
        if f in gps.data:
            _add_trace(fig, t, gps.data[f], label, TRACE_COLORS[i % len(TRACE_COLORS)], width=1)

    layout = _base_layout('GPS Uncertainty', '')
    layout['yaxis']['range'] = [0, 40]
    fig.update_layout(**layout)
    return fig


# 21. GPS Noise & Jamming
def graph_gps_noise(ulog):
    """GPS Noise per ms & Jamming Indicator"""
    gps = _find_topic(ulog, 'vehicle_gps_position')
    if gps is None:
        gps = _find_topic(ulog, 'sensor_gps')
    if gps is None:
        return None
    has_fields = 'noise_per_ms' in gps.data or 'jamming_indicator' in gps.data
    if not has_fields:
        return None
    fig = go.Figure()
    t = _get_time(gps)
    if 'noise_per_ms' in gps.data:
        _add_trace(fig, t, gps.data['noise_per_ms'], 'Noise per ms', TRACE_COLORS[0])
    if 'jamming_indicator' in gps.data:
        _add_trace(fig, t, gps.data['jamming_indicator'], 'Jamming Indicator', TRACE_COLORS[1], width=1)
    fig.update_layout(**_base_layout('GPS Noise & Jamming', ''))
    return fig


# 22. Power (Battery)
def graph_power(ulog):
    """Power: Voltage, Current, Discharged, Remaining"""
    bat = _find_topic(ulog, 'battery_status')
    if bat is None:
        return None
    fig = go.Figure()
    t = _get_time(bat)

    if 'voltage_v' in bat.data:
        _add_trace(fig, t, bat.data['voltage_v'], 'Battery Voltage [V]', TRACE_COLORS[0])
    elif 'voltage_filtered_v' in bat.data:
        _add_trace(fig, t, bat.data['voltage_filtered_v'], 'Battery Voltage [V]', TRACE_COLORS[0])

    if 'current_a' in bat.data:
        _add_trace(fig, t, bat.data['current_a'], 'Battery Current [A]', TRACE_COLORS[1], width=1)
    elif 'current_filtered_a' in bat.data:
        _add_trace(fig, t, bat.data['current_filtered_a'], 'Battery Current [A]', TRACE_COLORS[1], width=1)

    if 'discharged_mah' in bat.data:
        _add_trace(fig, t, bat.data['discharged_mah'] / 100, 'Discharged [mAh / 100]', TRACE_COLORS[2], width=1)

    if 'remaining' in bat.data:
        _add_trace(fig, t, bat.data['remaining'] * 10, 'Remaining [0=empty, 10=full]', TRACE_COLORS[3], width=1, dash='dot')

    fig.update_layout(**_base_layout('Power', ''))
    return fig


# 23. CPU & RAM
def graph_cpu_ram(ulog):
    """CPU & RAM Load"""
    cpu = _find_topic(ulog, 'cpuload')
    if cpu is None:
        return None
    fig = go.Figure()
    t = _get_time(cpu)

    if 'ram_usage' in cpu.data:
        _add_trace(fig, t, cpu.data['ram_usage'], 'RAM Usage', TRACE_COLORS[1])
    if 'load' in cpu.data:
        _add_trace(fig, t, cpu.data['load'], 'CPU Load', TRACE_COLORS[2])

    layout = _base_layout('CPU & RAM', '')
    layout['yaxis']['range'] = [0, 1]
    fig.update_layout(**layout)
    return fig


# 24. 2D Flight Path (XY)
def graph_flight_path_2d(ulog):
    """2D Flight Path: local XY plot"""
    lp = _find_topic(ulog, 'vehicle_local_position')
    if lp is None or 'x' not in lp.data or 'y' not in lp.data:
        return None

    fig = go.Figure()

    # Estimated path
    x_ds, y_ds = _downsample(np.asarray(lp.data['y'], dtype=np.float64),
                             np.asarray(lp.data['x'], dtype=np.float64))
    fig.add_trace(go.Scatter(x=x_ds, y=y_ds, name='Estimated', mode='lines',
                             line=dict(color=TRACE_COLORS[0], width=1.5)))

    # Setpoint path
    sp = _find_topic(ulog, 'vehicle_local_position_setpoint')
    if sp and 'x' in sp.data and 'y' in sp.data:
        xs, ys = _downsample(np.asarray(sp.data['y'], dtype=np.float64),
                             np.asarray(sp.data['x'], dtype=np.float64))
        fig.add_trace(go.Scatter(x=xs, y=ys, name='Setpoint', mode='lines',
                                 line=dict(color=TRACE_COLORS[1], width=1, dash='dot')))

    layout = _base_layout('Local Position', '[m]', height=500)
    layout['xaxis']['title'] = '[m]'
    layout['yaxis']['scaleanchor'] = 'x'
    layout['yaxis']['scaleratio'] = 1
    fig.update_layout(**layout)
    return fig


# 25. Acceleration Power Spectral Density (Spectrogram Heatmap)
def graph_accel_psd(ulog):
    """Acceleration PSD Spectrogram — green heatmap like PX4 Flight Review"""
    if not HAS_SCIPY:
        return None
    from scipy.signal import spectrogram

    sc = _find_topic(ulog, 'sensor_combined')
    if sc is None:
        return None

    t = _get_time(sc)
    if len(t) < 512:
        return None

    dt = np.median(np.diff(t))
    if dt <= 0:
        return None
    fs = 1.0 / dt

    axis_names = ['X', 'Y', 'Z']
    axis_fields = ['accelerometer_m_s2[0]', 'accelerometer_m_s2[1]', 'accelerometer_m_s2[2]']

    # Check which axes have data
    valid_axes = [(f, n) for f, n in zip(axis_fields, axis_names) if f in sc.data]
    if not valid_axes:
        return None

    nperseg = min(256, len(t) // 4)
    noverlap = nperseg // 2

    # Green colorscale matching PX4 Flight Review
    green_scale = [
        [0.0, '#000000'],
        [0.15, '#001a00'],
        [0.3, '#003300'],
        [0.45, '#006600'],
        [0.6, '#00aa00'],
        [0.75, '#00dd00'],
        [0.9, '#44ff44'],
        [1.0, '#ffffff'],
    ]

    figs = []
    for field, axis_name in valid_axes:
        accel = np.asarray(sc.data[field], dtype=np.float64)
        accel = accel - np.mean(accel)

        freqs, times, Sxx = spectrogram(accel, fs=fs, nperseg=nperseg,
                                         noverlap=noverlap, mode='psd')
        # Convert times to actual log time
        times = times * dt + t[0]
        # Log scale for better visibility
        Sxx_log = 10 * np.log10(np.maximum(Sxx, 1e-12))

        # Limit frequency range to useful range
        max_freq = min(fs / 2, 500)
        freq_mask = freqs <= max_freq
        freqs = freqs[freq_mask]
        Sxx_log = Sxx_log[freq_mask, :]

        fig = go.Figure()
        fig.add_trace(go.Heatmap(
            x=times, y=freqs, z=Sxx_log,
            colorscale=green_scale,
            colorbar=dict(title='dB', len=0.9),
            hovertemplate='Time: %{x:.1f}s<br>Freq: %{y:.1f}Hz<br>PSD: %{z:.1f}dB<extra></extra>',
        ))

        layout = _base_layout(
            f'Acceleration Power Spectral Density — {axis_name}',
            'Frequency [Hz]', height=GRAPH_HEIGHT
        )
        layout['xaxis']['title'] = 'Time (s)'
        fig.update_layout(**layout)
        figs.append((f'accel_psd_{axis_name.lower()}',
                     f'Accel PSD — {axis_name}', fig))

    return figs


# ============================================================
# Registry: exact PX4 Flight Review order
# ============================================================

STANDARD_GRAPHS = [
    ('flight_path', 'Local Position (2D)', graph_flight_path_2d),
    ('altitude', 'Altitude Estimate', graph_altitude),
    ('roll', 'Roll Angle', graph_roll),
    ('roll_rate', 'Roll Angular Rate', graph_roll_rate),
    ('pitch', 'Pitch Angle', graph_pitch),
    ('pitch_rate', 'Pitch Angular Rate', graph_pitch_rate),
    ('yaw', 'Yaw Angle', graph_yaw),
    ('yaw_rate', 'Yaw Angular Rate', graph_yaw_rate),
    ('local_pos_x', 'Local Position X', graph_local_pos_x),
    ('local_pos_y', 'Local Position Y', graph_local_pos_y),
    ('local_pos_z', 'Local Position Z', graph_local_pos_z),
    ('velocity', 'Velocity', graph_velocity),
    ('manual_control', 'Manual Control Inputs', graph_manual_control),
    ('actuator_controls', 'Actuator Controls', graph_actuator_controls),
    ('actuator_outputs', 'Actuator Outputs', graph_actuator_outputs),
    ('raw_accel', 'Raw Acceleration', graph_raw_accel),
    ('vibration', 'Vibration Metrics', graph_vibration),
    ('raw_gyro', 'Raw Angular Speed (Gyroscope)', graph_raw_gyro),
    ('magnetometer', 'Raw Magnetic Field Strength', graph_magnetometer),
    ('distance_sensor', 'Distance Sensor', graph_distance_sensor),
    ('gps_uncertainty', 'GPS Uncertainty', graph_gps_uncertainty),
    ('gps_noise', 'GPS Noise & Jamming', graph_gps_noise),
    ('power', 'Power', graph_power),
    ('cpu_ram', 'CPU & RAM', graph_cpu_ram),
    ('accel_psd', 'Acceleration Power Spectral Density', graph_accel_psd),
]


def generate_all_graphs(ulog):
    """Generate all available standard PX4 graphs. Returns list of (key, title, fig)."""
    results = []
    for key, title, fn in STANDARD_GRAPHS:
        try:
            result = fn(ulog)
            if result is None:
                continue
            # Some generators (PSD spectrogram) return a list of (key, title, fig)
            if isinstance(result, list):
                results.extend(result)
            else:
                results.append((key, title, result))
        except Exception as e:
            print(f"Warning: Could not generate {title}: {e}")
    return results
