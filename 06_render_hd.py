"""CC0 render-only presentation of the included approved native models.

Blender 4.3.2 --background --threads 2 --python scripts/render_hd.py --
    --source . --out . --audit ./render-audit --mode full

The model/GLB files, geometry, UVs, material nodes and packed pigment images
are never saved or changed. Only scene lights, camera, compositor and renderer
settings change in memory. Ginger's supplied FK clip is repeated in memory.
No photo, music, outside model or borrowed motion is read.
"""
import argparse, ast, hashlib, json, os, struct, sys, time
import bpy
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument('--source', required=True, help='v1.2.0 package directory')
parser.add_argument('--out', required=True, help='Output package directory')
parser.add_argument('--audit', required=True, help='Local validation/frame directory')
parser.add_argument('--mode', choices=['trial', 'full'], default='full')
parser.add_argument('--character', choices=['Ginger', 'Garlic', 'both'], default='both')
parser.add_argument('--fill-energy', type=float, default=100.0)
parser.add_argument('--fill-size', type=float, default=4.0)
parser.add_argument('--lower-fill-energy', type=float, default=80.0)
parser.add_argument('--lower-fill-size', type=float, default=4.0)
parser.add_argument('--fill-specular-factor', type=float, default=0.0)
parser.add_argument('--lower-fill-specular-factor', type=float, default=0.0)
parser.add_argument('--ginger-ortho', type=float, default=2.3)
parser.add_argument('--garlic-ortho', type=float, default=2.8)
parser.add_argument('--stop-file', help='Stop safely at the next frame boundary')
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
SOURCE, OUTPUT, AUDIT = map(os.path.abspath, (args.source, args.out, args.audit))
for directory in ('previews', 'animations'):
    os.makedirs(os.path.join(OUTPUT, directory), exist_ok=True)
os.makedirs(AUDIT, exist_ok=True)
sys.dont_write_bytecode = True

# Reuse only this package's transparent verification helpers and MP4 remuxer.
builder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'build_hd_revision.py')
with open(builder, encoding='utf-8') as stream:
    builder_text = stream.read()
saved_argv = sys.argv
sys.argv = ['build_hd_revision.py', '--', '--source', SOURCE, '--out', OUTPUT,
            '--audit', AUDIT, '--model-only']
helper = {'__name__': 'render_hd_helpers'}
exec(compile(builder_text.split('# Garlic canonical .blend:')[0], builder, 'exec'), helper)
sys.argv = saved_argv
remux_definition = next(node for node in ast.parse(builder_text).body
                        if isinstance(node, ast.FunctionDef) and node.name == 'faststart')
exec(compile(ast.Module(body=[remux_definition], type_ignores=[]), builder, 'exec'), helper)

def write_report(name, value):
    with open(os.path.join(AUDIT, name), 'w', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)

def signature():
    return {'meshes': {o.name: helper['mesh_sig'](o) for o in helper['model_meshes']()},
            'materials': helper['materials'](), 'images': helper['packed'](),
            'node_groups': {g.name: helper['node_sig'](g) for g in bpy.data.node_groups},
            'drivers': helper['driver_sig']()}

def snapshot():
    scene = bpy.context.scene
    background = next(node for node in scene.world.node_tree.nodes if node.type == 'BACKGROUND')
    lights = []
    for obj in bpy.data.objects:
        if obj.type == 'LIGHT':
            lights.append({'name': obj.name, 'type': obj.data.type, 'energy': obj.data.energy,
                           'color': list(obj.data.color), 'shape': obj.data.shape,
                           'specular_factor': getattr(obj.data, 'specular_factor', None),
                           'diffuse_factor': getattr(obj.data, 'diffuse_factor', None),
                           'size': obj.data.size, 'location': list(obj.location),
                           'rotation': list(obj.rotation_euler)})
    unsupported = [row['name'] + ':' + prop for row in lights
                   if row['name'] in {'Presentation Fill', 'Presentation lower soft fill'}
                   for prop in ['specular_factor', 'diffuse_factor'] if row[prop] is None]
    return {'engine': scene.render.engine, 'samples': scene.eevee.taa_render_samples,
            'denoising': False, 'denoiser': None, 'threads': scene.render.threads,
            'dimensions': [scene.render.resolution_x, scene.render.resolution_y],
            'fps': scene.render.fps, 'motion_blur': scene.render.use_motion_blur,
            'color_management': {'view_transform': scene.view_settings.view_transform,
                                 'look': scene.view_settings.look,
                                 'exposure': scene.view_settings.exposure,
                                 'gamma': scene.view_settings.gamma},
            'world': {'color': list(background.inputs['Color'].default_value),
                      'strength': background.inputs['Strength'].default_value},
            'lights': sorted(lights, key=lambda row: row['name']),
            'unsupported_light_controls': unsupported,
            'camera': {'type': scene.camera.data.type,
                       'ortho_scale': scene.camera.data.ortho_scale,
                       'location': list(scene.camera.location),
                       'rotation': list(scene.camera.rotation_euler)},
            'material_node_graphs_unchanged': True,
            'packed_pigment_png_bytes_unchanged': True}

def presentation(character):
    frames = [0, 12, 36, 60, 84] if character == 'Garlic' else [1, 7, 13, 19, 25]
    helper['hd_settings'](character, frames)
    scene = bpy.context.scene
    for obj in list(bpy.data.objects):
        if obj.type == 'LIGHT':
            bpy.data.objects.remove(obj, do_unlink=True)
    # Numeric studio settings from the approved source, without external assets.
    specifications = [
        ('Fill', args.fill_energy, (1.0, .87, .70), args.fill_size,
         (-3.0, -3.0, 1.6), (1.3844229, 0.0, -.7853982)),
        ('Key', 350.0, (1.0, .94, .84), 1.35,
         (2.2, -1.1, 2.8), (.8881090, 0.0, 1.1071488)),
        ('Rim', 135.0, (1.0, .88, .72), 1.15,
         (-1.8, 1.6, 2.7), (.9028407, 0.0, -2.2974386))]
    for name, energy, color, size, location, rotation in specifications:
        light = bpy.data.lights.new('Presentation ' + name, 'AREA')
        light.energy, light.color, light.size, light.shape = energy, color, size, 'SQUARE'
        if name == 'Fill':
            if hasattr(light, 'specular_factor'):
                light.specular_factor = args.fill_specular_factor
            if hasattr(light, 'diffuse_factor'):
                light.diffuse_factor = 1.0
        obj = bpy.data.objects.new(light.name, light)
        scene.collection.objects.link(obj)
        obj.location, obj.rotation_euler = location, rotation
    if args.lower_fill_energy > 0:
        light = bpy.data.lights.new('Presentation lower soft fill', 'AREA')
        light.energy, light.color = args.lower_fill_energy, (1.0, .94, .84)
        light.size, light.shape = args.lower_fill_size, 'DISK'
        if hasattr(light, 'specular_factor'):
            light.specular_factor = args.lower_fill_specular_factor
        if hasattr(light, 'diffuse_factor'):
            light.diffuse_factor = 1.0
        obj = bpy.data.objects.new(light.name, light)
        scene.collection.objects.link(obj)
        obj.location = (0.0, -3.0, .3)
        obj.rotation_euler = (helper['Vector']((0.0, 0.0, .8)) - obj.location).to_track_quat('-Z', 'Y').to_euler()
    background = next(node for node in scene.world.node_tree.nodes if node.type == 'BACKGROUND')
    background.inputs['Color'].default_value = (.8, .8, .8, 1)
    background.inputs['Strength'].default_value = .025
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.view_settings.exposure, scene.view_settings.gamma = .65, 1.0
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
    scene.eevee.taa_render_samples = 64
    scene.eevee.use_raytracing = False
    scene.render.fps, scene.render.fps_base = 24, 1.0
    scene.camera.data.ortho_scale = args.ginger_ortho if character == 'Ginger' else args.garlic_ortho
    return snapshot()

def ginger_render_loop():
    rig = bpy.data.objects['Ginger_Rig']
    clip = rig.animation_data.action.copy()
    clip.name = 'Ginger_HD_render_loop_only'
    rig.animation_data.action = clip
    for curve in clip.fcurves:
        for point in curve.keyframe_points:
            point.co.x = (point.co.x - 1) * 2
            point.handle_left.x = (point.handle_left.x - 1) * 2
            point.handle_right.x = (point.handle_right.x - 1) * 2
        curve.modifiers.new('CYCLES')
    bpy.context.scene.frame_set(0)

def safe_stop():
    if args.stop_file and os.path.isfile(args.stop_file):
        write_report('render_stopped.json', {'stopped_at_frame_boundary': True,
                                            'source_models_unchanged': True})
        raise SystemExit('Stop file found; partial frames remain only in the chosen audit directory')

def h264_container(path):
    """Read AVC SPS chroma from the actual MP4, without an outside executable."""
    with open(path, 'rb') as stream:
        blob = stream.read()
    def atoms(start, end):
        offset = start
        while offset < end:
            size, kind = struct.unpack_from('>I4s', blob, offset)
            header = 8
            if size == 1:
                size, header = struct.unpack_from('>Q', blob, offset + 8)[0], 16
            if size == 0:
                size = end - offset
            assert size >= header and offset + size <= end
            yield kind, offset, offset + header, offset + size
            offset += size
    top = list(atoms(0, len(blob)))
    moov = next(item for item in top if item[0] == b'moov')
    mdat = next(item for item in top if item[0] == b'mdat')
    assert moov[1] < mdat[1]
    def configurations(start, end):
        for kind, offset, payload, finish in atoms(start, end):
            if kind in {b'moov', b'trak', b'mdia', b'minf', b'stbl'}:
                yield from configurations(payload, finish)
            elif kind == b'stsd':
                for entry, _, entry_payload, entry_finish in atoms(payload + 8, finish):
                    if entry == b'avc1':
                        for child, _, child_payload, child_finish in atoms(entry_payload + 78, entry_finish):
                            if child == b'avcC':
                                yield blob[child_payload:child_finish]
    config = next(configurations(moov[2], moov[3]))
    assert config[0] == 1 and config[5] & 31
    length = struct.unpack_from('>H', config, 6)[0]
    sps = config[8:8 + length]
    assert sps and (sps[0] & 31) == 7
    rbsp = sps[1:].replace(b'\x00\x00\x03', b'\x00\x00')
    bits = ''.join(format(byte, '08b') for byte in rbsp)
    cursor = 0
    def read(count):
        nonlocal cursor
        result = int(bits[cursor:cursor + count], 2)
        cursor += count
        return result
    def ue():
        zeros = 0
        while read(1) == 0:
            zeros += 1
        return (1 << zeros) - 1 + (read(zeros) if zeros else 0)
    profile = read(8)
    read(8)
    level = read(8)
    ue()
    chroma, luma_depth, chroma_depth = 1, 8, 8
    if profile in {100, 110, 122, 244, 44, 83, 86, 118, 128, 138, 139, 134, 135}:
        chroma = ue()
        if chroma == 3:
            read(1)
        luma_depth, chroma_depth = ue() + 8, ue() + 8
    assert (chroma, luma_depth, chroma_depth) == (1, 8, 8), 'Actual movie must be 8-bit YUV420'
    return {'sample_entry': 'avc1', 'profile_idc': profile, 'level_idc': level,
            'chroma_format_idc': chroma, 'pixel_format': 'yuv420p',
            'bit_depth_luma': luma_depth, 'bit_depth_chroma': chroma_depth,
            'moov_before_mdat': True}

def encode_frames(character, paths):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps, scene.render.fps_base = 24, 1.0
    scene.render.resolution_x = scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.render.threads_mode, scene.render.threads = 'FIXED', 2
    scene.frame_start, scene.frame_end = 0, 95
    scene.view_settings.view_transform, scene.view_settings.look = 'Standard', 'None'
    scene.view_settings.exposure, scene.view_settings.gamma = 0, 1
    scene.render.use_sequencer, scene.render.use_compositing = True, False
    editor = scene.sequence_editor_create()
    strip = editor.sequences.new_image('Native material rendered frames', paths[0], channel=1, frame_start=0)
    for path in paths[1:]:
        strip.elements.append(os.path.basename(path))
    strip.frame_final_duration = len(paths)
    assert strip.frame_duration == 96
    scene.render.image_settings.file_format = 'FFMPEG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.ffmpeg.format, scene.render.ffmpeg.codec = 'MPEG4', 'H264'
    scene.render.ffmpeg.constant_rate_factor, scene.render.ffmpeg.ffmpeg_preset = 'HIGH', 'GOOD'
    scene.render.ffmpeg.audio_codec, scene.render.ffmpeg.gopsize = 'NONE', 24
    filename = 'Garlic_body_motion_1080p.mp4' if character == 'Garlic' else 'Ginger_FK_motion_1080p.mp4'
    path = os.path.join(OUTPUT, 'animations', filename)
    scene.render.filepath = path
    safe_stop()
    bpy.ops.render.render(animation=True)
    faststart = helper['faststart'](path)
    return {'file': 'animations/' + filename, 'frames': 96, 'fps': 24, 'seconds': 4,
            'dimensions': [1080, 1080], 'codec': 'H264', 'audio': False,
            'faststart': faststart, 'actual_container': h264_container(path),
            'sha256': helper['sha'](path), 'bytes': os.path.getsize(path)}

def decode_movie(row):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps, scene.render.fps_base = 24, 1.0
    scene.render.resolution_x = scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.render.threads_mode, scene.render.threads = 'FIXED', 2
    strip = scene.sequence_editor_create().sequences.new_movie(
        'Actual final H264 decode', os.path.join(OUTPUT, row['file']), channel=1, frame_start=0)
    assert strip.frame_duration == 96
    assert (strip.elements[0].orig_width, strip.elements[0].orig_height) == (1080, 1080)
    scene.render.use_sequencer, scene.render.use_compositing = True, False
    scene.view_settings.view_transform, scene.view_settings.look = 'Standard', 'None'
    scene.view_settings.exposure, scene.view_settings.gamma = 0, 1
    for frame in [0, 12, 36]:
        safe_stop()
        helper['render_still'](os.path.join(AUDIT, os.path.basename(row['file']) + '_decoded_%03d.png' % frame), frame)
    row['actual_movie_decode'] = {'frames': 96, 'dimensions': [1080, 1080], 'sample_frames': [0, 12, 36]}

source_hashes = {name: helper['sha'](os.path.join(SOURCE, folder, name))
                 for folder, name in [('models', 'Ginger_rigged.blend'), ('models', 'Garlic_body_motion.blend'),
                                     ('glb', 'Ginger_rigged.glb'), ('glb', 'Garlic_body_motion.glb')]}
characters = ['Garlic', 'Ginger'] if args.character == 'both' else [args.character]
videos, previews = [], []
for character in characters:
    safe_stop()
    filename = 'Garlic_body_motion.blend' if character == 'Garlic' else 'Ginger_rigged.blend'
    helper['open_blend'](os.path.join(SOURCE, 'models', filename))
    helper['no_unexpected_assets']()
    before = signature()
    actual_settings = presentation(character)
    if character == 'Ginger' and args.mode == 'full':
        ginger_render_loop()
    assert signature() == before
    preview_samples = [('trial', 0), ('hop', 12), ('tilt', 36)] if character == 'Garlic' else [('trial', 0), ('arms', 12), ('legs', 24)]
    if args.mode == 'trial':
        preview_samples = preview_samples[:1]
    for label, frame in preview_samples:
        safe_stop()
        relative = 'previews/' + character + '_1080p_' + label + '.png'
        helper['render_still'](os.path.join(OUTPUT, relative), frame)
        previews.append({'file': relative, 'frame': frame, 'render_settings': actual_settings,
                         'sha256': helper['sha'](os.path.join(OUTPUT, relative))})
    assert signature() == before
    write_report('render_preview_verification.json', {'previews': previews, 'source_hashes': source_hashes})
    print(character, 'PRESENTATION PREVIEWS VERIFIED', flush=True)
    if args.mode == 'trial':
        continue
    directory = os.path.join(AUDIT, 'render_frames', character)
    os.makedirs(directory, exist_ok=True)
    paths, frame_times = [], []
    for frame in range(96):
        safe_stop()
        path = os.path.join(directory, '%03d.png' % frame)
        started = time.monotonic()
        helper['render_still'](path, frame)
        paths.append(path)
        frame_times.append(time.monotonic() - started)
        write_report('render_progress.json', {'character': character, 'completed_frames': frame + 1,
                                             'target_frames': 96, 'seconds': sum(frame_times)})
        print(character, 'FRAME', frame + 1, '/96', round(frame_times[-1], 2), 's', flush=True)
    assert signature() == before
    # Snapshot the actual scene immediately before leaving it for image encoding.
    actual_settings = snapshot()
    row = encode_frames(character, paths)
    row['render_settings'] = actual_settings
    row['render_seconds'] = round(sum(frame_times), 3)
    row['source_native_sha256'] = source_hashes[filename]
    decode_movie(row)
    videos.append(row)
    write_report('video_progress.json', videos)
    print(character, 'HD VIDEO VERIFIED', flush=True)

for folder, name in [('models', 'Ginger_rigged.blend'), ('models', 'Garlic_body_motion.blend'),
                     ('glb', 'Ginger_rigged.glb'), ('glb', 'Garlic_body_motion.glb')]:
    assert helper['sha'](os.path.join(SOURCE, folder, name)) == source_hashes[name]
report = {'source_models_glb_bytes_unchanged': True, 'source_hashes': source_hashes,
          'videos': videos, 'previews': previews, 'renderer_scene_only': True,
          'appearance_note': 'Approved pigment/material graphs are retained. Lighting, renderer and framing are documented; exact prior dance movie pixel identity is not claimed.'}
write_report('hd_render_verification.json', report)
print('RENDER-ONLY COMPLETE - MODEL/GLB FILES UNCHANGED', flush=True)
