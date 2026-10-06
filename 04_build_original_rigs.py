"""Preserve approved Blender meshes; add FK limb controls and a small test action.

Run with Blender 4.3.2 --background --threads 2 --python this.py -- --source-dir DIR --output-dir DIR --audit-dir DIR.
No source file is written. GLB appearance is baked separately after saving the canonical .blend.
"""
import bpy, os, sys, json, math, hashlib, array, argparse, time
from mathutils import Vector, Quaternion

argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
p=argparse.ArgumentParser()
p.add_argument('--source-dir',required=True)
p.add_argument('--output-dir',required=True)
p.add_argument('--audit-dir',required=True)
p.add_argument('--only',choices=['Ginger','Garlic'])
args=p.parse_args(argv)
OUT=args.output_dir; AUD=args.audit_dir
for sub in ['models','glb','previews','animations','docs','scripts']: os.makedirs(os.path.join(OUT,sub),exist_ok=True)
os.makedirs(AUD,exist_ok=True)

def filehash(path):
    with open(path,'rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
def meshhash(o):
    d=array.array('f',[0])*(len(o.data.vertices)*3); o.data.vertices.foreach_get('co',d)
    h=hashlib.sha256(d.tobytes())
    for poly in o.data.polygons: h.update(array.array('I',poly.vertices).tobytes())
    return h.hexdigest()
def mesh_snapshot(objects):
    bpy.context.view_layer.update(); dg=bpy.context.evaluated_depsgraph_get()
    r={}
    for o in objects:
        if o.type!='MESH': continue
        e=o.evaluated_get(dg); m=e.to_mesh()
        values=[e.matrix_world@v.co for v in m.vertices]
        r[o.name]={'raw_geometry_sha256':meshhash(o),'materials':[x.name if x else None for x in o.data.materials],'shape_keys':[(k.name,len(k.data)) for k in o.data.shape_keys.key_blocks] if o.data.shape_keys else [],'positions':values,'evaluated_vertices':len(m.vertices)}
        e.to_mesh_clear()
    return r
def compare_rest(before,objects):
    after=mesh_snapshot(objects); rows=[]
    for name,b in before.items():
        a=after[name]; assert a['raw_geometry_sha256']==b['raw_geometry_sha256'],name
        assert a['materials']==b['materials'],name
        assert a['shape_keys']==b['shape_keys'],name
        assert a['evaluated_vertices']==b['evaluated_vertices'],name
        delta=max(((x-y).length for x,y in zip(a['positions'],b['positions'])),default=0)
        assert delta<2e-5,(name,delta)
        rows.append({'mesh':name,'raw_geometry_sha256':a['raw_geometry_sha256'],'raw_geometry_identical':True,'material_slots_identical':True,'shape_keys_identical':True,'evaluated_vertices':a['evaluated_vertices'],'evaluated_rest_world_max_delta':delta})
    return rows
def cleanup_metadata():
    cleared=0
    # Current face drivers address transforms, not custom properties. Keep any future property targets.
    keep={}
    for o in bpy.data.objects:
        if o.animation_data:
            for f in o.animation_data.drivers:
                for v in f.driver.variables:
                    for t in v.targets:
                        if t.id and t.data_path.startswith('["'):
                            key=t.data_path.split('"')[1]; keep.setdefault(t.id.name,set()).add(key)
    for coll in [bpy.data.objects,bpy.data.meshes,bpy.data.armatures,bpy.data.materials,bpy.data.images,bpy.data.collections,bpy.data.scenes,bpy.data.worlds,bpy.data.node_groups,bpy.data.actions]:
        for item in coll:
            for key in list(item.keys()):
                if key not in keep.get(item.name,set()): del item[key]; cleared+=1
    for t in list(bpy.data.texts): bpy.data.texts.remove(t)
    for i in bpy.data.images:
        if i.packed_file: i.filepath='//../textures/'+os.path.basename(i.filepath.replace('\\','/'))
    for scene in bpy.data.scenes:
        scene.render.filepath='//../previews/'
    return {'custom_properties_removed':cleared,'embedded_texts':len(bpy.data.texts),'linked_libraries':[os.path.basename(l.filepath) for l in bpy.data.libraries]}
def add_bone(arm,name,head,tail,parent=None):
    b=arm.data.edit_bones.new(name); b.head=head; b.tail=tail
    if parent: b.parent=arm.data.edit_bones[parent]
    return b
def make_garlic_rig(originals):
    controller=next(o for o in originals if o.type=='EMPTY' and 'approved body' in o.name)
    body=next(o for o in originals if o.type=='MESH' and 'continuous solid sculpt' in o.name)
    ad=bpy.data.armatures.new('Garlic FK armature'); rig=bpy.data.objects.new('Garlic_Rig',ad); bpy.context.scene.collection.objects.link(rig)
    bpy.ops.object.select_all(action='DESELECT'); rig.select_set(True); bpy.context.view_layer.objects.active=rig
    bpy.ops.object.mode_set(mode='EDIT')
    add_bone(rig,'root',(0,0,-.30),(0,0,-.12))
    add_bone(rig,'body',(0,0,0),(0,0,1.1),'root')
    for suffix,sign in [('L',-1),('R',1)]:
        add_bone(rig,'arm.'+suffix,(sign*.77,.015,.49),(sign*1.12,.015,.45),'body')
        add_bone(rig,'leg.'+suffix,(sign*.37,.015,.065),(sign*.39,-.01,-.20),'root')
    bpy.ops.object.mode_set(mode='OBJECT'); bpy.context.view_layer.update()
    world=controller.matrix_world.copy()
    controller.parent=rig; controller.parent_type='BONE'; controller.parent_bone='body'
    bpy.context.view_layer.update(); controller.matrix_world=world; bpy.context.view_layer.update()
    limbs=bpy.data.collections.new('ADDED LIMBS - toggle viewport and render'); bpy.context.scene.collection.children.link(limbs)
    made=[]
    for suffix,sign in [('L',-1),('R',1)]:
        for part,center,scale in [('arm',(sign*.99,.015,.46),(.265,.115,.12)),('leg',(sign*.39,-.01,-.115),(.115,.145,.185))]:
            bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=16,location=center)
            o=bpy.context.object; o.name='Garlic added rounded '+part+'.'+suffix; o.scale=scale
            bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
            for c in list(o.users_collection): c.objects.unlink(o)
            limbs.objects.link(o)
            for poly in o.data.polygons: poly.use_smooth=True
            o.data.materials.append(body.data.materials[0])
            group=o.vertex_groups.new(name=part+'.'+suffix); group.add(list(range(len(o.data.vertices))),1,'REPLACE')
            mod=o.modifiers.new('FK limb deformation','ARMATURE'); mod.object=rig; mod.use_deform_preserve_volume=True
            o.parent=rig
            made.append(o)
    return rig,made,limbs
def style_rig(rig):
    rig.show_in_front=True; rig.data.display_type='STICK'
    for b in rig.pose.bones:
        b.rotation_mode='XYZ'; b.lock_scale=(True,True,True)
        if b.name not in ['root','body']: b.lock_location=(True,True,True)
        # Single, rounded FK limbs have no elbow/knee; ranges avoid severe attachment stretching.
        if b.name.startswith(('arm.','leg.')):
            c=b.constraints.new('LIMIT_ROTATION'); c.name='Recommended gentle FK range'; c.owner_space='LOCAL'; c.use_limit_x=True; c.use_limit_y=True; c.use_limit_z=True
            lim=math.radians(35 if b.name.startswith('arm.') else 22)
            c.min_x=c.min_y=c.min_z=-lim; c.max_x=c.max_y=c.max_z=lim
        b.bone.color.palette='THEME04' if b.name.startswith('arm.') else ('THEME03' if b.name.startswith('leg.') else 'THEME01')
    rig['rig_usage']='FK rounded limbs; Pose Mode; root moves all, body moves torso/face; see docs/RIG_USAGE.md'
    rig['license']='CC0-1.0'
    rig['front_direction']='-Y; Z up; L/R preserve existing screen-side naming'
def world_axis_euler(rig,name,axis,angle):
    b=rig.pose.bones[name]
    local=rig.data.bones[name].matrix_local.to_quaternion().inverted()@Vector(axis)
    return Quaternion(local,angle).to_euler('XYZ')
def make_action(rig,prefix):
    a=bpy.data.actions.new(prefix+'_FK_motion_check'); a.use_fake_user=True
    rig.animation_data_create(); rig.animation_data.action=a
    scene=bpy.context.scene; scene.render.fps=12; scene.frame_start=1; scene.frame_end=25
    # 2-second loop. Deliberately small world-Y swings make the four limbs easy to see from the front.
    keys=[(1,0,0),(7,1,0),(13,0,1),(19,-.5,-1),(25,0,0)]
    for frame,arm_t,leg_t in keys:
        for bone in rig.pose.bones:
            bone.location=(0,0,0); bone.rotation_euler=(0,0,0); bone.scale=(1,1,1)
        for suffix,sign in [('L',-1),('R',1)]:
            rig.pose.bones['arm.'+suffix].rotation_euler=world_axis_euler(rig,'arm.'+suffix,(0,1,0),math.radians(25)*arm_t*sign)
            rig.pose.bones['leg.'+suffix].rotation_euler=world_axis_euler(rig,'leg.'+suffix,(0,1,0),math.radians(15)*leg_t*sign)
        for bone in rig.pose.bones:
            bone.keyframe_insert('rotation_euler',frame=frame,group=bone.name)
    for fc in a.fcurves:
        for kp in fc.keyframe_points: kp.interpolation='BEZIER'
    for frame,label in [(1,'Rest'),(7,'Arms'),(13,'Legs'),(19,'All limbs'),(25,'Rest loop')]: scene.timeline_markers.new(label,frame=frame)
    scene.frame_set(1)
    return a
def motion_audit(rig,mesh_objects):
    scene=bpy.context.scene; out=[]
    scene.frame_set(1); baseline=mesh_snapshot(mesh_objects)
    for name in ['arm.L','arm.R','leg.L','leg.R']:
        # Evaluate each limb independently, away from the action, against the same rest mesh.
        old=rig.animation_data.action; rig.animation_data.action=None
        for b in rig.pose.bones: b.rotation_euler=(0,0,0)
        rig.pose.bones[name].rotation_euler=world_axis_euler(rig,name,(0,1,0),math.radians(20 if name.startswith('arm') else 15))
        bpy.context.view_layer.update(); posed=mesh_snapshot(mesh_objects)
        changes=[]
        for meshname,b in baseline.items():
            maximum=max(((x-y).length for x,y in zip(posed[meshname]['positions'],b['positions'])),default=0)
            moved=sum((x-y).length>1e-5 for x,y in zip(posed[meshname]['positions'],b['positions']))
            if moved: changes.append({'mesh':meshname,'moved_vertices':moved,'max_displacement':maximum})
        assert changes,(name,'No deformation')
        out.append({'bone':name,'tested_rotation_world_axis':'Y','tested_degrees':20 if name.startswith('arm') else 15,'moved_meshes':changes})
        for b in rig.pose.bones: b.rotation_euler=(0,0,0)
        rig.animation_data.action=old; scene.frame_set(1)
    weights=[]
    for o in mesh_objects:
        if o.type!='MESH' or not any(m.type=='ARMATURE' and m.object==rig for m in o.modifiers): continue
        sums=[sum(g.weight for g in v.groups if o.vertex_groups[g.group].name in rig.data.bones) for v in o.data.vertices]
        weights.append({'mesh':o.name,'vertices':len(sums),'unweighted_vertices':sum(v<.999 for v in sums),'sum_min':min(sums),'sum_max':max(sums),'groups':[g.name for g in o.vertex_groups]})
        assert max(abs(x-1) for x in sums)<1e-4,(o.name,'weights not normalized')
    scene.frame_set(1)
    return out,weights
def presentation_setup(prefix):
    scene=bpy.context.scene
    coll=bpy.data.collections.new('PREVIEW - cameras and lights'); scene.collection.children.link(coll)
    def link(o): coll.objects.link(o); return o
    target=Vector((0,0,.68 if prefix=='Garlic' else .76))
    cd=bpy.data.cameras.new('Preview camera'); camera=link(bpy.data.objects.new('Preview camera',cd)); camera.location=(0,-7,target.z+.22)
    camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler(); cd.type='ORTHO'; cd.ortho_scale=2.80 if prefix=='Garlic' else 1.95; scene.camera=camera
    for name,location,energy,size in [('Key',(-3,-4,5),650,4),('Fill',(3,-3,2),450,4),('Rim',(0,2,3),350,3)]:
        ld=bpy.data.lights.new('Preview '+name,'AREA'); ld.energy=energy; ld.shape='DISK'; ld.size=size
        o=link(bpy.data.objects.new('Preview '+name,ld)); o.location=location; o.rotation_euler=(target-o.location).to_track_quat('-Z','Y').to_euler()
    scene.render.engine='CYCLES'; scene.cycles.device='CPU'; scene.cycles.samples=8; scene.cycles.use_denoising=False
    scene.render.threads_mode='FIXED'; scene.render.threads=2
    scene.render.resolution_x=480; scene.render.resolution_y=480; scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'; scene.render.image_settings.color_mode='RGBA'; scene.render.film_transparent=True
    scene.world.use_nodes=True; scene.world.node_tree.nodes.get('Background').inputs['Strength'].default_value=.25
    return coll
def render_to(path,samples=8,size=480):
    s=bpy.context.scene; s.cycles.samples=samples; s.render.resolution_x=s.render.resolution_y=size; s.render.filepath=path
    bpy.ops.render.render(write_still=True)
def glb_bake_export(prefix,rig,mesh_objects):
    scene=bpy.context.scene; scene.frame_set(1)
    scene.render.engine='CYCLES'; scene.cycles.device='CPU'; scene.cycles.samples=1; scene.render.bake.target='VERTEX_COLORS'; scene.render.bake.use_pass_direct=False; scene.render.bake.use_pass_indirect=False
    properties={}
    for m in bpy.data.materials:
        if not m.use_nodes: continue
        bsdf=next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
        if not bsdf: continue
        properties[m.name]={'roughness':float(bsdf.inputs['Roughness'].default_value),'metallic':float(bsdf.inputs['Metallic'].default_value)}
        nt=m.node_tree; emission=nt.nodes.new('ShaderNodeEmission'); emission.inputs['Strength'].default_value=1
        if bsdf.inputs['Base Color'].is_linked: nt.links.new(bsdf.inputs['Base Color'].links[0].from_socket,emission.inputs['Color'])
        else: emission.inputs['Color'].default_value=bsdf.inputs['Base Color'].default_value
        output=next(n for n in nt.nodes if n.type=='OUTPUT_MATERIAL' and n.is_active_output)
        for l in list(output.inputs['Surface'].links): nt.links.remove(l)
        nt.links.new(emission.outputs[0],output.inputs['Surface'])
    rows=[]
    for o in mesh_objects:
        if o.type!='MESH': continue
        raw=meshhash(o)
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active=o
        colors=o.data.color_attributes.new(name='Export_Baked_Albedo',type='FLOAT_COLOR',domain='CORNER'); index=list(o.data.color_attributes).index(colors)
        o.data.color_attributes.active_color_index=index; o.data.color_attributes.render_color_index=index
        bpy.ops.object.bake(type='EMIT',use_clear=True)
        values=array.array('f',[0])*(len(colors.data)*4); colors.data.foreach_get('color',values)
        for i in range(3,len(values),4): values[i]=1
        colors.data.foreach_set('color',values)
        original=o.data.materials[0]; props=properties.get(original.name,{})
        mat=bpy.data.materials.new(o.name+' | baked PBR'); mat.use_nodes=True; bsdf=mat.node_tree.nodes.get('Principled BSDF')
        color=mat.node_tree.nodes.new('ShaderNodeVertexColor'); color.layer_name='Export_Baked_Albedo'; mat.node_tree.links.new(color.outputs['Color'],bsdf.inputs['Base Color'])
        bsdf.inputs['Roughness'].default_value=max(.25,min(.65,props.get('roughness',.5)))
        bsdf.inputs['Metallic'].default_value=props.get('metallic',0); bsdf.inputs['Alpha'].default_value=1
        o.data.materials.clear(); o.data.materials.append(mat)
        for attr in list(o.data.color_attributes):
            if attr.name!='Export_Baked_Albedo': o.data.color_attributes.remove(attr)
        assert meshhash(o)==raw
        rows.append({'mesh':o.name,'corners':len(values)//4,'albedo_min':[min(values[i::4]) for i in range(3)],'albedo_max':[max(values[i::4]) for i in range(3)]})
    bpy.ops.object.select_all(action='DESELECT')
    for o in bpy.data.objects:
        if o.type in ['MESH','ARMATURE','EMPTY']: o.select_set(True)
    props={x.identifier for x in bpy.ops.export_scene.gltf.get_rna_type().properties}
    options={'filepath':os.path.join(OUT,'glb',prefix+'_rigged.glb'),'export_format':'GLB','use_selection':True,'export_animations':True,'export_animation_mode':'ACTIONS','export_skins':True,'export_morph':True,'export_morph_normal':True,'export_yup':True,'export_apply':prefix=='Garlic','export_extras':False,'export_normals':True,'export_texcoords':True,'export_materials':'EXPORT','export_vertex_color':'MATERIAL','export_all_vertex_colors':False,'export_frame_range':True,'export_frame_step':1,'export_force_sampling':True}
    options={k:v for k,v in options.items() if k in props}; bpy.ops.export_scene.gltf(**options)
    return {'method':'Cycles EMIT bake of final Principled Base Color to per-corner FLOAT_COLOR, PBR roughness approximation. Canonical .blend material graphs unchanged.','meshes':rows,'size_bytes':os.path.getsize(options['filepath']),'options':{k:v for k,v in options.items() if k!='filepath'}}
def build(prefix,fname):
    started=time.monotonic(); src=os.path.join(args.source_dir,fname); source_hash=filehash(src)
    bpy.ops.wm.open_mainfile(filepath=src,load_ui=False,use_scripts=False)
    scene=bpy.context.scene; scene.frame_set(1)
    originals=list(bpy.data.objects); before=mesh_snapshot(originals)
    original_image_hashes={i.name:hashlib.sha256(i.packed_file.data).hexdigest() for i in bpy.data.images if i.packed_file}
    assert not bpy.data.libraries,'External library linked data is not distributable'
    cleanup=cleanup_metadata()
    added=[]; limbs=None
    if prefix=='Garlic': rig,added,limbs=make_garlic_rig(originals)
    else: rig=bpy.data.objects['Ginger_Rig']
    style_rig(rig); action=make_action(rig,prefix)
    rest=compare_rest(before,originals)
    image_hashes={i.name:hashlib.sha256(i.packed_file.data).hexdigest() for i in bpy.data.images if i.packed_file}; assert image_hashes==original_image_hashes
    motions,weights=motion_audit(rig,originals+added)
    presentation_setup(prefix)
    scene.frame_set(1)
    # Preview source appearance with the same canonical camera/material settings.
    if limbs: limbs.hide_render=True
    render_to(os.path.join(OUT,'previews',prefix+'_preserved_original.png'))
    if limbs: limbs.hide_render=False
    render_to(os.path.join(OUT,'previews',prefix+'_rigged_rest.png'))
    scene.frame_set(19); render_to(os.path.join(OUT,'previews',prefix+'_rigged_motion.png'))
    scene.frame_set(1); scene.render.filepath='//../previews/'+prefix+'_rigged_rest.png'
    scene.cycles.samples=8; scene.render.resolution_x=scene.render.resolution_y=480
    bpy.ops.object.select_all(action='DESELECT'); rig.select_set(True); bpy.context.view_layer.objects.active=rig
    for area in bpy.context.screen.areas if bpy.context.screen else []:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_distance=3.4
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,'models',prefix+'_rigged.blend'),check_existing=False,compress=True,relative_remap=False)
    # The optional limbs live in their own collection and can be disabled; no new body mesh replaces the approved sculpt.
    frames=os.path.join(AUD,prefix+'_frames'); os.makedirs(frames,exist_ok=True)
    for f in range(1,25):
        scene.frame_set(f); render_to(os.path.join(frames,'%03d.png'%f),samples=4,size=256)
        print('RENDERED',prefix,f,flush=True)
    scene.frame_set(1)
    glb=glb_bake_export(prefix,rig,originals+added)
    report={'model':fname,'source_sha256':source_hash,'source_file_unchanged':filehash(src)==source_hash,'blender_version':bpy.app.version_string,'canonical_blend':prefix+'_rigged.blend','original_meshes_rest':rest,'original_texture_bytes_identical':image_hashes==original_image_hashes,'packed_images':[{'name':i.name,'packed':bool(i.packed_file)} for i in bpy.data.images if i.source=='FILE'],'added_meshes':[o.name for o in added],'added_limbs_optional_collection':limbs.name if limbs else None,'bones':[{'name':b.name,'head':list(b.head_local),'tail':list(b.tail_local),'local_x_world':list(b.matrix_local.to_3x3().col[0]),'local_y_world':list(b.matrix_local.to_3x3().col[1]),'local_z_world':list(b.matrix_local.to_3x3().col[2]),'parent':b.parent.name if b.parent else None} for b in rig.data.bones],'motion_tests':motions,'weights':weights,'action':{'name':action.name,'frames':[1,25],'fps':12,'seconds':2,'motion':'Gentle world-Y FK wave/step, arms 25deg and legs 15deg; does not change sculpt or source action.'},'metadata_cleanup':cleanup,'glb':glb,'elapsed_seconds':round(time.monotonic()-started,2),'known_limits':['FK single-piece rounded limbs, no elbow or knee joints.','Source .blend is appearance authority; GLB bakes base color and approximates roughness, scattering, bump, and procedural shader details.','Garlic expression drivers and Geometry Nodes remain in .blend; GLB exports the initial expression as evaluated mesh, not the Blender expression controls.']}
    assert report['source_file_unchanged']
    with open(os.path.join(AUD,prefix+'_rig_audit.json'),'w',encoding='utf-8') as f: json.dump(report,f,ensure_ascii=False,indent=2)
    print('FINISHED',prefix,report['elapsed_seconds'],flush=True)
for prefix,fn in [('Ginger','Ginger_v20.blend'),('Garlic','Garlic_v14.blend')]:
    if not args.only or prefix==args.only: build(prefix,fn)
