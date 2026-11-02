# The bowled lanes' own rigs: on each a small armature carries the ten pins and the lane's balls, so the web plays the
# roll and the strike like any act (a lane is a performer; its act and the bowler's start together). While the bowler
# carries a ball it follows his hand (sampled from his act); released, it rolls down the lane hooking into the 1-3
# pocket; the pins it meets fly back and out, tumbling, and knock down the ones beside them (a scripted strike:
# ballistic pins bouncing on the deck, off the kickbacks and into the pit); the sweep clears the deck, a new rack
# comes down from under the masking, the ball comes back up the return and out onto the rack's rails.
import math, random
import bpy, bmesh
from mathutils import Vector, Matrix, Quaternion
import cine, people
import rooms.the_big_lebowski as R

S = R.SCALE
FPS = people.FPS
PIN_H, PIN_R = 0.381, 0.06
DECK_Z = 0.034                                     # the lane's top
G = Vector((0, 0, -9.81))


def make_rig(name, lane, balls, M, col):
    """An armature at the room's origin: a root, a bone per pin (at its spot on `lane`) and per ball (at its rest on
    the pair's rack, `balls` = [(material name, rack slot)]); one mesh, each part skinned wholly to its bone. Built at
    true size, shrunk with the room. Returns (armature, mesh)."""
    y = R.LANES[lane]; pair = next(a for a, b in R.PAIRS if lane in (a, b))
    arm = bpy.data.objects.new(name, bpy.data.armatures.new(name)); col.objects.link(arm)
    bpy.context.view_layer.objects.active = arm; arm.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm.data.edit_bones
    root = eb.new(f'{name}_root'); root.head = Vector((R.X_FOUL, y, 0)) * S; root.tail = root.head + Vector((0, 0, 0.1 * S))
    parts = []
    for k, (px, dy) in enumerate(R.PIN_SPOTS):
        b = eb.new(f'{name}_pin{k + 1}'); b.head = Vector((px, y + dy, DECK_Z)) * S; b.tail = b.head + Vector((0, 0, PIN_H * S)); b.parent = root
        parts.append(('pin', b.name, Vector((px, y + dy, DECK_Z))))
    for k, (mat, slot) in enumerate(balls):
        c = R.RACK_SPOTS[pair][slot]
        b = eb.new(f'{name}_ball{k}'); b.head = c * S; b.tail = b.head + Vector((0, 0, 0.1 * S)); b.parent = root
        parts.append(('ball', b.name, c.copy(), mat))
    bpy.ops.object.mode_set(mode='OBJECT')
    bm = bmesh.new(); groups = {}
    mats = [M['pin'], M['pin_red']] + [M[p[3]] for p in parts if p[0] == 'ball']
    for p in parts:
        n0 = len(bm.verts)
        if p[0] == 'pin':
            fs = R.pin_bm(bm, M_idx=(0, 1), xf=Matrix.Translation(p[2]))
        else:
            out = R.ball_bm(bm, p[2]); fs = list({f for v in out['verts'] for f in v.link_faces})
            for f in fs: f.material_index = mats.index(M[p[3]]); f.smooth = True
            _holes(bm, p[2], mats.index(M['black']) if M['black'] in mats else None)
        bm.verts.ensure_lookup_table()
        groups[p[1]] = list(range(n0, len(bm.verts)))
    if M['black'] not in mats: mats.append(M['black'])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.transform(Matrix.Scale(S, 4))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for m in mats: me.materials.append(m)
    mesh = bpy.data.objects.new(f'{name}_parts', me); col.objects.link(mesh)
    for bone, ids in groups.items():
        vg = mesh.vertex_groups.new(name=bone); vg.add(ids, 1.0, 'REPLACE')
    md = mesh.modifiers.new('rig', 'ARMATURE'); md.object = arm; mesh.parent = arm
    for o in (arm, mesh): o['person'] = name
    for pb in arm.pose.bones: pb.rotation_mode = 'QUATERNION'
    arm['rest'] = {p[1]: list(p[2]) for p in parts}
    return arm, mesh


def _holes(bm, c, mat):
    """The ball's three finger holes: small dark discs on its top (a little forward), set into the surface."""
    if mat is None: return
    for dx, dy in ((0.03, -0.022), (0.03, 0.022), (-0.035, 0.0)):
        d = Vector((dx, dy, 0.1)).normalized(); p = c + d * (R.BALL_R + 0.0005); r = 0.011
        u = d.orthogonal().normalized(); v = d.cross(u)
        vs = [bm.verts.new(p + (u * math.cos(2 * math.pi * k / 8) + v * math.sin(2 * math.pi * k / 8)) * r) for k in range(8)]
        f = bm.faces.new(vs); f.material_index = mat


class Lane:
    """One act of a lane rig: where every part is at every frame (true metres), keyed onto its bones at the end."""
    def __init__(self, arm, lane, n):
        self.arm, self.lane, self.n = arm, lane, n
        self.y = R.LANES[lane]
        self.rest = {k: Vector(v) for k, v in arm['rest'].items()}
        self.track = {k: [(self.rest[k].copy(), Quaternion()) for _ in range(n + 1)] for k in self.rest}

    def set(self, part, f, pos, rot=Quaternion()):
        if 0 <= f <= self.n: self.track[part][f] = (pos.copy(), rot.copy())

    def hold_from(self, part, f0):
        """Hold a part where it is at f0 to the end."""
        p, q = self.track[part][f0]
        for f in range(f0, self.n + 1): self.track[part][f] = (p.copy(), q.copy())

    def key(self, action_name, f_start):
        """Key every bone: its pose matrix carries its rest geometry to where the part is (rotations about the part's
        own rest point: a pin's foot, a ball's centre)."""
        arm = self.arm; act = bpy.data.actions.new(action_name); act.use_fake_user = True
        arm.animation_data_create(); arm.animation_data.action = act
        if act.slots and arm.animation_data.action_slot is None: arm.animation_data.action_slot = act.slots[0]
        for part, frames in self.track.items():
            pb = arm.pose.bones[part]; rest = self.rest[part] * S; L = pb.bone.matrix_local
            for f, (pos, rot) in enumerate(frames):
                T = Matrix.Translation(pos * S) @ rot.to_matrix().to_4x4() @ Matrix.Translation(-rest)
                pb.matrix = T @ L
                pb.keyframe_insert('location', frame=f_start + f); pb.keyframe_insert('rotation_quaternion', frame=f_start + f)
        root = arm.pose.bones[f'{arm.name}_root']
        for f in (f_start, f_start + self.n):
            root.keyframe_insert('location', frame=f); root.keyframe_insert('rotation_quaternion', frame=f)
        act.frame_range = (f_start, f_start + self.n)
        return act


def rest_act(arm, lane, name, seconds=4.0, f_start=1):
    """Nothing moving: the pins standing, the balls on the rack."""
    return Lane(arm, lane, int(seconds * FPS)).key(name, f_start)


def bowl_act(arm, lane, name, n, ball, hand_path, release, f_start=1, seed=1, others=()):
    """A lane's act for one ball: `hand_path` {frame: true-metre ball centre} while the bowler carries it (to the
    `release` frame), then the roll, the strike, the sweep, the new rack and the ball's return. Returns the action
    and the frame the pins are hit."""
    L = Lane(arm, lane, n); rnd = random.Random(seed)
    for f, p in hand_path.items(): L.set(ball, f, p)
    f_grab = min(hand_path)
    p_rel = hand_path[release]
    # the roll: from the release down the lane, hooking into the 1-3 pocket (right-handed: the pocket on -y)
    y_pocket = L.y - 0.064; x_head = R.X_HEAD
    v = 6.2                                                                         # m/s (the lane is half its length)
    x0 = p_rel.x; x_end = R.X_MACH - 0.04 - R.BALL_R
    pos = []; t = 0.0; x = x0; rot = Quaternion(); prev = p_rel.copy()
    zr = DECK_Z + R.BALL_R
    while x < x_end + 1e-6:
        x = x0 + v * t
        u = min(max((x - x0) / (x_head - x0), 0.0), 1.2)
        y = p_rel.y + (y_pocket - p_rel.y) * (3 * u * u - 2 * u * u * u if u <= 1 else 1 + (u - 1) * 0.6)
        if x < x0 + 0.5: z = p_rel.z + (zr - p_rel.z) * min(1, (x - x0) / 0.5) ** 0.5     # set down onto the lane
        elif x < R.X_PIT: z = zr
        else: z = max(-0.08 + R.BALL_R, zr - 2.5 * (x - R.X_PIT) ** 1.5)              # over the pit's edge
        p = Vector((min(x, x_end), y, z)); d = p - prev
        if d.length > 1e-6:
            ax = Vector((0, 0, 1)).cross(d.normalized()); ax = ax.normalized() if ax.length > 1e-6 else Vector((0, 1, 0))
            rot = Quaternion(ax, d.length / R.BALL_R) @ rot
        pos.append((p, rot.copy())); prev = p; t += 1 / FPS
        if x >= x_end: break
    for i, (p, q) in enumerate(pos): L.set(ball, release + 1 + i, p, q)
    f_pit = release + 1 + len(pos)
    hid = Vector((R.X_PIT + 0.15, L.y, -0.6))                                         # down the return, out of sight
    for f in range(f_pit + 8, n + 1): L.set(ball, f, hid)
    # the pins: struck in a chain from the pocket
    f_hit = next((release + 1 + i for i, (p, q) in enumerate(pos) if p.x >= x_head - 0.17), f_pit)
    hit_at = {}; src = {}
    ball_line = [(release + 1 + i, p) for i, (p, q) in enumerate(pos)]
    spots = {k: Vector((px, L.y + dy, DECK_Z)) for k, (px, dy) in enumerate(R.PIN_SPOTS)}
    for k, s in spots.items():                                                      # met by the ball itself
        for f, p in ball_line:
            if (Vector((p.x, p.y, 0)) - Vector((s.x, s.y, 0))).length < R.BALL_R + 0.065:
                hit_at[k] = f; src[k] = p.copy(); break
    for _ in range(4):                                                              # then by their neighbours
        for k, s in spots.items():
            if k in hit_at: continue
            near = sorted(((s - spots[j]).length, j) for j in hit_at)
            if near:
                d, j = near[0]; hit_at[k] = hit_at[j] + int((0.06 + 0.16 * d / 0.3048) * FPS); src[k] = spots[j] + Vector((0, 0, 0.12))
    pins = [f'{arm.name}_pin{k + 1}' for k in range(10)]
    y_lo, y_hi = L.y - R.LW / 2 - R.GW - 0.02, L.y + R.LW / 2 + R.GW + 0.02
    f_sweep = f_hit + int(4.0 * FPS); f_set = f_hit + int(5.4 * FPS)
    for k, s in spots.items():
        name_ = pins[k]; fh = hit_at[k]
        d = Vector((s.x - src[k].x, s.y - src[k].y, 0)); d = d.normalized() if d.length > 1e-6 else Vector((1, 0, 0))
        d = (d + Vector((0.9, 0, 0))).normalized()                                  # thrown back as well as out
        speed = rnd.uniform(2.4, 3.6) if k in (0, 1, 2) else rnd.uniform(1.4, 2.6)
        dist = speed * 0.38; Tf = rnd.uniform(0.45, 0.65); hop = 0.05 + 0.04 * speed
        axis = Vector((0, 0, 1)).cross(d).normalized(); fall = math.pi / 2 + rnd.uniform(-0.15, 0.25)
        yaw_rate = rnd.uniform(-7.0, 7.0); twist = rnd.uniform(-0.6, 0.6)
        ring = ([Vector((PIN_R * 0.45 * math.cos(a), PIN_R * 0.45 * math.sin(a), 0)) for a in (0, 2.1, 4.2)]      # the pin's outline
                + [Vector((PIN_R * math.cos(a), PIN_R * math.sin(a), 0.114)) for a in (0, 1.6, 3.1, 4.7)] + [Vector((0, 0, PIN_H))])
        for f in range(fh, f_sweep + 1):
            t = (f - fh) / FPS; u = min(1.0, t / Tf); e = 1 - (1 - u) ** 2                        # out fast, settling
            h = s + d * dist * e
            if h.y < y_lo + 0.06 or h.y > y_hi - 0.06:                                            # off the kickbacks
                wall = y_lo + 0.06 if h.y < y_lo + 0.06 else y_hi - 0.06; h.y = 2 * wall - h.y
            h.x = min(h.x, R.X_MACH - 0.1)
            spin = Quaternion(Vector((0, 0, 1)), yaw_rate * min(t, Tf * 1.6) * 0.25 + twist)
            q = spin @ Quaternion(axis, fall * min(1.0, u * 1.15))
            floor = DECK_Z if h.x < R.X_PIT else -0.08
            low = min((q @ v).z for v in ring)
            z = floor - low + (hop * math.sin(math.pi * u) if u < 1 else 0.0)
            L.set(name_, f, Vector((h.x, h.y, z)), q)                                # (about its foot: the part's rest point)
        L.hold_from(name_, f_sweep)
        # the sweep: what lies on the deck slides back into the pit; everything goes out of sight below it
        p0, q0 = L.track[name_][f_sweep]
        for f in range(f_sweep, f_sweep + int(0.8 * FPS)):
            u = (f - f_sweep) / (0.8 * FPS)
            pp = p0.copy()
            if p0.x < R.X_PIT: pp.x = p0.x + (R.X_PIT + 0.15 - p0.x) * u * u; pp.z = p0.z if pp.x < R.X_PIT else p0.z - (pp.x - R.X_PIT) * 1.2
            L.set(name_, f, pp, q0)
        for f in range(f_sweep + int(0.8 * FPS), f_set): L.set(name_, f, Vector((R.X_PIT + 0.15, s.y, -0.6)))
        # the new rack, lowered from under the masking onto its spots
        for f in range(f_set, n + 1):
            u = min(1.0, (f - f_set) / (1.4 * FPS)); u = u * u * (3 - 2 * u)
            L.set(name_, f, Vector((s.x, s.y, DECK_Z + (R.MASK_Z[0] + 0.02 - DECK_Z) * (1 - u))))
    # the ball comes back up the return and rolls out onto the rails
    pair = next(a for a, b in R.PAIRS if L.lane in (a, b))
    f_back = f_hit + int(7.0 * FPS); rest = L.rest[ball]; hood = Vector((R.X_HOOD, R.PAIR_Y[pair], rest.z))
    for f in range(f_back, n + 1):
        u = min(1.0, (f - f_back) / (1.3 * FPS)); u = 1 - (1 - u) ** 2
        p = hood.lerp(rest, u)
        rot = Quaternion(Vector((0, -1, 0)), -(hood - p).length / R.BALL_R)
        L.set(ball, f, p, rot)
    if f_back > n: cine.log(f'{name}: the act ends before the ball is back ({f_back} > {n})')
    for o in others: L.hold_from(o, 0)
    cine.log(f'{name}: grab {f_grab}, release {release}, pins hit {f_hit}, sweep {f_sweep}, rack {f_set}, ball back {f_back} of {n}')
    return L.key(name, f_start), f_hit
