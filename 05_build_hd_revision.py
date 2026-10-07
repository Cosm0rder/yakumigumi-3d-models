"""CC0: existing approved assets, rig-only Garlic revision and original-material HD renders.
No reference image, external model, borrowed animation, music or font is read.
Source files are never saved. Ginger blend/GLB are byte-copied unchanged.
Use --model-only to reproduce the native/GLB revision without rendering.
Final HD presentation is rendered separately with render_hd.py.
Run with Blender 4.3.2 --background --threads 2 --python this.py -- --source DIR --out DIR --audit DIR --model-only.
"""
import bpy,os,sys,json,math,hashlib,struct,shutil,argparse,time
import numpy as np
from mathutils import Vector,Quaternion
p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--out',required=True);p.add_argument('--audit',required=True);p.add_argument('--await-file');p.add_argument('--model-only',action='store_true');a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
SRC=os.path.abspath(a.source);OUT=os.path.abspath(a.out);AUD=os.path.abspath(a.audit);CLIP='Garlic_Body_bounce_check'
for folder in ['models','glb','animations','previews','scripts']:os.makedirs(os.path.join(OUT,folder),exist_ok=True)
os.makedirs(AUD,exist_ok=True);sys.dont_write_bytecode=True
LIMBS={'arm.L','arm.R','leg.L','leg.R'};ADDED={'Garlic added rounded '+n for n in LIMBS}
FPS=24;FRAMES=96;GRANT='CC0-1.0: Commercial use, modification and redistribution permitted by the owner.'

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def dump(name,d):
    with open(os.path.join(AUD,name),'w',encoding='utf-8') as f:json.dump(d,f,ensure_ascii=False,indent=2)
def open_blend(path):
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.wm.open_mainfile(filepath=path,load_ui=False,use_scripts=False)
    bpy.context.scene.render.threads_mode='FIXED';bpy.context.scene.render.threads=2
def no_unexpected_assets():
    for key in ['libraries','texts','sounds','movieclips','cache_files']:assert len(getattr(bpy.data,key))==0,key
    assert not any(any(k in x.name.lower() for k in ['nintendo','snoopy','.vmd']) for group in ['objects','meshes','materials','actions'] for x in getattr(bpy.data,group))
def array_hash(data,prop,width,dtype):
    v=np.empty(len(data)*width,dtype=dtype);data.foreach_get(prop,v);return hashlib.sha256(v.tobytes()).hexdigest()
def mesh_sig(o):
    m=o.data
    return {'vertices':len(m.vertices),'polygons':len(m.polygons),'coordinates':array_hash(m.vertices,'co',3,np.float32),'loop_vertices':array_hash(m.loops,'vertex_index',1,np.int32),'polygon_starts':array_hash(m.polygons,'loop_start',1,np.int32),'polygon_sizes':array_hash(m.polygons,'loop_total',1,np.int32),'polygon_materials':array_hash(m.polygons,'material_index',1,np.int32),'uv':{u.name:array_hash(u.data,'uv',2,np.float32) for u in m.uv_layers},'colors':{c.name:array_hash(c.data,'color',4,np.float32) for c in m.color_attributes},'materials':[x.name if x else None for x in m.materials],'shape_keys':{k.name:array_hash(k.data,'co',3,np.float32) for k in m.shape_keys.key_blocks} if m.shape_keys else {}}
def value(v):
    if isinstance(v,(str,int,float,bool)):return v
    if hasattr(v,'name'):return {'id_name':v.name}
    try:return [float(x) for x in v]
    except (TypeError,ValueError):return str(type(v).__name__)
def node_sig(tree):
    if not tree:return None
    rows=[]
    for n in tree.nodes:
        r={'name':n.name,'type':n.bl_idname,'inputs':{str(i)+':'+s.name:value(s.default_value) for i,s in enumerate(n.inputs) if hasattr(s,'default_value')}}
        for key in ['operation','blend_type','distribution','interpolation','extension','projection','noise_dimensions','normalize']:
            if hasattr(n,key):r[key]=value(getattr(n,key))
        if hasattr(n,'image') and n.image:r['image']=n.image.name
        if hasattr(n,'node_tree') and n.node_tree:r['group']=n.node_tree.name
        rows.append(r)
    data={'nodes':rows,'links':sorted((l.from_node.name,l.from_socket.identifier,l.to_node.name,l.to_socket.identifier) for l in tree.links)}
    return hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def materials():return {m.name:node_sig(m.node_tree) for m in bpy.data.materials}
def packed():
    rows={}
    for i in bpy.data.images:
        if i.name=='Render Result':continue
        assert i.source=='FILE' and i.packed_file,(i.name,'missing packed texture')
        expected='//../textures/'+os.path.basename(i.filepath.replace('\\','/'))
        assert i.filepath.replace('\\','/')==expected
        assert all(p.filepath.replace('\\','/')==expected for p in i.packed_files)
        rows[i.name]={'sha256':hashlib.sha256(i.packed_file.data).hexdigest(),'path':expected,'packed':True}
    return rows
def driver_sig():
    result=[]
    for o in bpy.data.objects:
        if not o.animation_data:continue
        for d in o.animation_data.drivers:
            result.append({'object':o.name,'path':d.data_path,'index':d.array_index,'expression':d.driver.expression,'variables':[{'name':v.name,'type':v.type,'targets':[{'id':t.id.name if t.id else None,'path':t.data_path,'transform_type':t.transform_type,'transform_space':t.transform_space} for t in v.targets]} for v in d.driver.variables]})
    return result
def display_helpers():
    return {b.custom_shape for o in bpy.data.objects if o.type=='ARMATURE' for b in o.pose.bones if b.custom_shape}
def model_meshes():
    helpers=display_helpers();return [o for o in bpy.data.objects if o.type=='MESH' and o not in helpers]
def positions():
    bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();result={}
    for o in model_meshes():
        if o.hide_render:continue
        e=o.evaluated_get(dg);m=e.to_mesh();c=np.empty(len(m.vertices)*3,dtype=np.float32);m.vertices.foreach_get('co',c);matrix=np.array(e.matrix_world,dtype=np.float64);result[o.name]=c.reshape((-1,3)) @ matrix[:3,:3].T+matrix[:3,3];e.to_mesh_clear()
    return result
def changed(before,after):
    return {n:float(np.linalg.norm(p-before[n],axis=1).max(initial=0)) for n,p in after.items()}
def clear_actions(rig):
    rig.animation_data_create();rig.animation_data.action=None
    for o in bpy.data.objects:
        if o.animation_data:
            for t in list(o.animation_data.nla_tracks):o.animation_data.nla_tracks.remove(t)
    for action in list(bpy.data.actions):bpy.data.actions.remove(action,do_unlink=True)
def remove_appendages(rig):
    removed=[]
    for n in sorted(ADDED):
        o=bpy.data.objects.get(n);assert o and o.type=='MESH',n;m=o.data;bpy.data.objects.remove(o,do_unlink=True)
        if m.users==0:bpy.data.meshes.remove(m)
        removed.append(n)
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT')
    for n in sorted(LIMBS):assert n in rig.data.edit_bones;rig.data.edit_bones.remove(rig.data.edit_bones[n])
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in bpy.data.objects:
        if o.type=='MESH':
            for g in list(o.vertex_groups):
                if g.name in LIMBS:o.vertex_groups.remove(g)
    c=bpy.data.collections.get('ADDED LIMBS - toggle viewport and render')
    if c:assert not c.objects;bpy.data.collections.remove(c)
    assert set(rig.data.bones.keys())=={'root','body'}
    return removed
def body_action(rig):
    clear_actions(rig);act=bpy.data.actions.new(CLIP);act.use_fake_user=True;rig.animation_data.action=act
    s=bpy.context.scene;s.render.fps=FPS;s.frame_start=0;s.frame_end=96
    for frame,hop,tilt in [(0,0,0),(12,.075,0),(24,0,0),(36,0,8),(48,0,0),(60,.075,0),(72,0,0),(84,0,-8),(96,0,0)]:
        for b in rig.pose.bones:b.location=(0,0,0);b.rotation_mode='XYZ';b.rotation_euler=(0,0,0);b.scale=(1,1,1)
        world_to_rig=rig.matrix_world.to_3x3().inverted();root_to_local=rig.data.bones['root'].matrix_local.to_3x3().inverted()
        rig.pose.bones['root'].location=root_to_local@(world_to_rig@Vector((0,0,hop)))
        axis=rig.data.bones['body'].matrix_local.to_quaternion().inverted()@(world_to_rig@Vector((0,1,0)))
        rig.pose.bones['body'].rotation_euler=Quaternion(axis,math.radians(tilt)).to_euler('XYZ')
        for b in rig.pose.bones:b.keyframe_insert('location',frame=frame,group=b.name);b.keyframe_insert('rotation_euler',frame=frame,group=b.name)
    for fc in act.fcurves:
        for kp in fc.keyframe_points:kp.interpolation='BEZIER'
    rig['rig_usage']='No hands or feet. root translates the approved body; body tilts it. Existing expression drivers remain in blend.';rig['license']=GRANT
    s.frame_set(0);return act
def motion_check():
    s=bpy.context.scene;s.frame_set(0);rest=positions();s.frame_set(12);hop=positions();s.frame_set(36);tilt=positions();s.frame_set(0)
    hops=changed(rest,hop);tilts=changed(rest,tilt);assert all(abs(v-.075)<2e-5 for v in hops.values());assert all(v>1e-5 for v in tilts.values())
    return {'hop_frame12_max_displacements':hops,'tilt_frame36_max_displacements':tilts,'all_visible_body_and_face_meshes_follow_root_and_body':True}
def hd_settings(prefix,frames):
    s=bpy.context.scene;s.render.engine='BLENDER_EEVEE_NEXT'
    if hasattr(s,'eevee') and hasattr(s.eevee,'taa_render_samples'):s.eevee.taa_render_samples=64
    if hasattr(s,'eevee') and hasattr(s.eevee,'use_raytracing'):s.eevee.use_raytracing=False
    s.render.resolution_x=s.render.resolution_y=1080;s.render.resolution_percentage=100;s.render.threads_mode='FIXED';s.render.threads=2;s.render.use_motion_blur=False
    s.render.film_transparent=True;s.render.use_sequencer=False;s.render.use_compositing=True;s.use_nodes=True
    for helper in display_helpers():helper.hide_render=True
    lower=bpy.data.objects.get('HD soft lower-front fill')
    if not lower:
        light=bpy.data.lights.new('HD soft lower-front fill','AREA');lower=bpy.data.objects.new(light.name,light);s.collection.objects.link(lower)
    lower.data.energy=280;lower.data.shape='DISK';lower.data.size=4.5;lower.location=(0,-4,-.35);lower.rotation_euler=(Vector((0,0,.6))-lower.location).to_track_quat('-Z','Y').to_euler()
    nt=s.node_tree;nt.nodes.clear();layer=nt.nodes.new('CompositorNodeRLayers');background=nt.nodes.new('CompositorNodeRGB');background.outputs[0].default_value=(.91,.925,.95,1);over=nt.nodes.new('CompositorNodeAlphaOver');over.inputs[0].default_value=1;nt.links.new(background.outputs[0],over.inputs[1]);nt.links.new(layer.outputs['Image'],over.inputs[2]);comp=nt.nodes.new('CompositorNodeComposite');nt.links.new(over.outputs[0],comp.inputs[0])
    # Fit actual deformed extents in the retained front-camera orientation.
    camera=s.camera;coords=[]
    for f in frames:s.frame_set(f);coords.extend(positions().values())
    points=np.concatenate(coords);center=Vector(((points[:,0].min()+points[:,0].max())*.5,(points[:,1].min()+points[:,1].max())*.5,(points[:,2].min()+points[:,2].max())*.5))
    forward=camera.rotation_euler.to_quaternion()@Vector((0,0,-1));camera.location=center-forward*7
    inverse=np.array(camera.matrix_world.inverted(),dtype=np.float64);p=points@inverse[:3,:3].T+inverse[:3,3];camera.data.type='ORTHO';camera.data.ortho_scale=max(float(np.ptp(p[:,0])),float(np.ptp(p[:,1])))*1.17
    s.frame_set(frames[0]);s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGB';s.render.filepath='//../previews/'+prefix+'_1080p_trial.png'
    return {'engine':s.render.engine,'samples':64,'motion_blur':False,'resolution':[1080,1080],'original_material_graphs_retained':True,'studio_background':True,'soft_lower_front_fill_energy':280,'ortho_scale':camera.data.ortho_scale}
def render_still(path,frame):
    s=bpy.context.scene;s.frame_set(frame);s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGB';s.render.filepath=path;bpy.ops.render.render(write_still=True)
def glb_doc(path):
    with open(path,'rb') as f:magic,version,size=struct.unpack('<4sII',f.read(12));length,kind=struct.unpack('<II',f.read(8));d=json.loads(f.read(length))
    assert magic==b'glTF' and version==2 and size==os.path.getsize(path) and kind==0x4e4f534a
    return d
def export_glb(path):
    bpy.ops.object.select_all(action='DESELECT')
    helpers=display_helpers()
    for o in bpy.data.objects:
        if o.type in ('MESH','ARMATURE','EMPTY') and o not in helpers:o.select_set(True)
    props={x.identifier for x in bpy.ops.export_scene.gltf.get_rna_type().properties};options={'filepath':path,'export_format':'GLB','use_selection':True,'export_animations':True,'export_animation_mode':'ACTIONS','export_skins':True,'export_yup':True,'export_apply':False,'export_extras':False,'export_normals':True,'export_texcoords':True,'export_materials':'EXPORT','export_vertex_color':'MATERIAL','export_all_vertex_colors':False,'export_frame_range':True,'export_frame_step':1,'export_force_sampling':True}
    bpy.ops.export_scene.gltf(**{k:v for k,v in options.items() if k in props})
def save_garlic():
    path=os.path.join(OUT,'models','Garlic_body_motion.blend');bpy.context.scene.frame_set(0);bpy.context.preferences.filepaths.save_version=0
    for i in bpy.data.images:
        if i.name=='Render Result':continue
        i.filepath='//../textures/'+os.path.basename(i.filepath.replace('\\','/'))
        for pf in i.packed_files:pf.filepath=i.filepath
    bpy.ops.wm.save_as_mainfile(filepath=path,check_existing=False,compress=True,relative_remap=False)
    return path

# Garlic canonical .blend: remove only the explicit added appendages and replace FK action.
source_hashes={n:sha(os.path.join(SRC,folder,n)) for folder,n in [('models','Ginger_rigged.blend'),('models','Garlic_rigged.blend'),('glb','Ginger_rigged.glb'),('glb','Garlic_rigged.glb')]}
open_blend(os.path.join(SRC,'models','Garlic_rigged.blend'));no_unexpected_assets();bpy.context.scene.frame_set(1)
rig=bpy.data.objects['Garlic_Rig'];originals={o.name:mesh_sig(o) for o in bpy.data.objects if o.type=='MESH' and o.name not in ADDED};before_positions={n:v for n,v in positions().items() if n in originals};before_materials=materials();before_groups={g.name:node_sig(g) for g in bpy.data.node_groups};before_images=packed();before_drivers=driver_sig();assert len(before_drivers)==6
removed=remove_appendages(rig);body_action(rig);assert {o.name:mesh_sig(o) for o in bpy.data.objects if o.type=='MESH'}==originals;assert materials()==before_materials;assert {g.name:node_sig(g) for g in bpy.data.node_groups}==before_groups;assert packed()==before_images;assert driver_sig()==before_drivers
rest_delta=changed(before_positions,positions());assert max(rest_delta.values())<2e-5
controller=next(o for o in bpy.data.objects if o.type=='EMPTY' and 'approved body' in o.name.lower());assert controller.parent==rig and controller.parent_type=='BONE' and controller.parent_bone=='body'
for n in originals:
    parent=bpy.data.objects[n].parent;chain=[]
    while parent:chain.append(parent);parent=parent.parent
    assert controller in chain,n
motion=motion_check();render_settings=hd_settings('Garlic',[0,12,36,60,84]);garlic_blend=save_garlic()
open_blend(garlic_blend);assert {o.name:mesh_sig(o) for o in bpy.data.objects if o.type=='MESH'}==originals;assert materials()==before_materials and packed()==before_images and driver_sig()==before_drivers;assert set(bpy.data.objects['Garlic_Rig'].data.bones.keys())=={'root','body'};assert [x.name for x in bpy.data.actions]==[CLIP];motion_check();no_unexpected_assets()
native_report={'file':'Garlic_body_motion.blend','removed_appendage_objects':removed,'removed_bones':sorted(LIMBS),'bones':['root','body'],'clip':CLIP,'fps':24,'frame_range':[0,96],'seconds':4,'original_mesh_geometry_uv_material_slots_identical':True,'original_material_node_graphs_identical':True,'original_geometry_node_groups_identical':True,'original_packed_png_bytes_identical':True,'face_drivers_identical_count':6,'source_rest_max_displacement':max(rest_delta.values()),'original_mesh_signatures':originals,'images':before_images,'motion':motion,'render':render_settings}
dump('garlic_native_preservation.json',native_report)
print('GARLIC NATIVE REVISION VERIFIED',flush=True)
if not a.model_only:render_still(os.path.join(OUT,'previews','Garlic_1080p_trial.png'),0)

# GLB uses the already-approved baked PBR/vertex colors, never the canonical shader graphs.
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=24;bpy.ops.import_scene.gltf(filepath=os.path.join(SRC,'glb','Garlic_rigged.glb'))
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');rig.animation_data_create();old_action=next(x for x in bpy.data.actions if x.name.startswith('Garlic_FK_motion_check'));rig.animation_data.action=old_action
for t in rig.animation_data.nla_tracks:t.mute=True
bpy.context.scene.frame_set(1);glb_originals={o.name:mesh_sig(o) for o in model_meshes() if o.name not in ADDED};glb_rest={n:v for n,v in positions().items() if n in glb_originals};glb_materials=materials();remove_appendages(rig);clear_actions(rig)
for o in model_meshes():
    matrix=o.matrix_world.copy();o.parent=rig;o.parent_type='OBJECT';o.parent_bone='';o.matrix_world=matrix
    for g in list(o.vertex_groups):o.vertex_groups.remove(g)
    group=o.vertex_groups.new(name='body');group.add(list(range(len(o.data.vertices))),1.0,'REPLACE')
    for m in list(o.modifiers):
        if m.type=='ARMATURE':o.modifiers.remove(m)
    mod=o.modifiers.new('Body bone rigid deformation','ARMATURE');mod.object=rig
body_action(rig);assert {o.name:mesh_sig(o) for o in model_meshes()}==glb_originals;assert materials()==glb_materials;assert max(changed(glb_rest,positions()).values())<2e-5;motion_check();glb_path=os.path.join(OUT,'glb','Garlic_body_motion.glb');export_glb(glb_path)
document=glb_doc(glb_path);assert [x.get('name') for x in document['animations']]==[CLIP];assert [len(x['joints']) for x in document['skins']]==[2];assert not any('uri' in x for key in ['images','buffers'] for x in document.get(key,[]));assert not ADDED.intersection({x.get('name') for x in document.get('nodes',[])})
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=24;bpy.ops.import_scene.gltf(filepath=glb_path);rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');assert set(rig.data.bones.keys())=={'root','body'};rig.animation_data_create();rig.animation_data.action=next(x for x in bpy.data.actions if x.name.startswith(CLIP))
for t in rig.animation_data.nla_tracks:t.mute=True
glb_motion=motion_check();assert not any(o.name in ADDED for o in bpy.data.objects)
weights=[]
for o in model_meshes():
    sums=[sum(g.weight for g in v.groups) for v in o.data.vertices];assert sums and max(abs(s-1) for s in sums)<1e-5;weights.append({'mesh':o.name,'vertices':len(sums),'weight_sum_min':min(sums),'weight_sum_max':max(sums)})
glb_report={'file':'Garlic_body_motion.glb','sha256':sha(glb_path),'bytes':os.path.getsize(glb_path),'mesh_count':len(document['meshes']),'color_mesh_count':sum(any('COLOR_0' in p['attributes'] for p in m['primitives']) for m in document['meshes']),'skin_joint_counts':[2],'bone_names':['root','body'],'clip':CLIP,'fps':24,'seconds':4,'sample_frames':{'rest':0,'hop':12,'tilt':36},'sample_seconds':{'rest':0,'hop':.5,'tilt':1.5},'all_external_resources':0,'existing_baked_pbr_vertex_colors_preserved':True,'fresh_factory_import_passed':True,'weights':weights,'motion':glb_motion}
dump('garlic_glb_verification.json',glb_report);print('GARLIC GLB REVISION VERIFIED',flush=True)

# Ginger source remains byte-identical; HD render settings are only in memory.
for folder in ['models','glb']:shutil.copy2(os.path.join(SRC,folder,'Ginger_rigged.'+('blend' if folder=='models' else 'glb')),os.path.join(OUT,folder,'Ginger_rigged.'+('blend' if folder=='models' else 'glb')))
open_blend(os.path.join(OUT,'models','Ginger_rigged.blend'));no_unexpected_assets();assert set(bpy.data.objects['Ginger_Rig'].data.bones.keys())=={'root','body'}|LIMBS;ginger_images=packed();ginger_render=hd_settings('Ginger',[1,7,13,19,25])
if not a.model_only:render_still(os.path.join(OUT,'previews','Ginger_1080p_trial.png'),1)

if a.model_only:
    dump('model_revision_verification.json',{'garlic_native':native_report,'garlic_glb':glb_report,'ginger_bytecopies_unchanged':True,'source_hashes':source_hashes,'rendered':False})
    print('MODEL-ONLY REVISION COMPLETE - NO RENDERS OR VIDEOS',flush=True)
    sys.exit(0)
dump('trial_ready.json',{'trial_images':['previews/Garlic_1080p_trial.png','previews/Ginger_1080p_trial.png'],'garlic':native_report,'ginger_render':ginger_render,'garlic_glb':glb_report,'full_animation_started':False})
print('1080P TRIALS READY - FULL ANIMATION NOT STARTED',flush=True)
if a.await_file:
    while not os.path.isfile(a.await_file):time.sleep(1)
print('FULL ANIMATION GATE RELEASED',flush=True)

# Helpers for direct H264 rendering and MP4 faststart without an external executable.
def faststart(path):
    blob=open(path,'rb').read();atoms=[];pos=0
    while pos<len(blob):
        size,kind=struct.unpack_from('>I4s',blob,pos);header=8
        if size==1:size=struct.unpack_from('>Q',blob,pos+8)[0];header=16
        if size==0:size=len(blob)-pos
        assert size>=header and pos+size<=len(blob);atoms.append((kind,pos,size,header));pos+=size
    moov=next(x for x in atoms if x[0]==b'moov');mdat=next(x for x in atoms if x[0]==b'mdat')
    if moov[1]<mdat[1]:return {'moov_before_mdat':True,'remuxed':False}
    assert moov==atoms[-1],'Unexpected atom order; do not guess offsets'
    prefix_end=mdat[1];shift=moov[2];m=bytearray(blob[moov[1]:moov[1]+moov[2]])
    containers={b'moov',b'trak',b'mdia',b'minf',b'stbl',b'edts',b'dinf',b'udta'}
    def update(start,end):
        i=start
        while i<end:
            size,kind=struct.unpack_from('>I4s',m,i);head=8
            if size==1:size=struct.unpack_from('>Q',m,i+8)[0];head=16
            assert size>=head and i+size<=end
            if kind in (b'stco',b'co64'):
                count=struct.unpack_from('>I',m,i+head+4)[0];width=4 if kind==b'stco' else 8;fmt='>I' if width==4 else '>Q'
                for j in range(count):
                    offset=i+head+8+j*width;old=struct.unpack_from(fmt,m,offset)[0];assert old>=prefix_end and old<moov[1];struct.pack_into(fmt,m,offset,old+shift)
            elif kind in containers:update(i+head,i+size)
            i+=size
    update(moov[3],len(m));temp=path+'.faststart.tmp'
    with open(temp,'wb') as f:f.write(blob[:prefix_end]);f.write(m);f.write(blob[prefix_end:moov[1]])
    os.replace(temp,path);return {'moov_before_mdat':True,'remuxed':True,'method':'Move moov before mdat and update stco/co64 offsets; video payload bytes untouched'}
def direct_video(prefix,name,start):
    s=bpy.context.scene;s.render.fps=24;s.frame_start=start;s.frame_end=start+95;s.render.image_settings.file_format='FFMPEG';s.render.image_settings.color_mode='RGB';s.render.ffmpeg.format='MPEG4';s.render.ffmpeg.codec='H264';s.render.ffmpeg.constant_rate_factor='HIGH';s.render.ffmpeg.ffmpeg_preset='GOOD';s.render.ffmpeg.audio_codec='NONE';s.render.ffmpeg.gopsize=24
    path=os.path.join(OUT,'animations',name);s.render.filepath=path;bpy.ops.render.render(animation=True);assert os.path.getsize(path)>0;f=faststart(path)
    return {'file':'animations/'+name,'frames':96,'fps':24,'seconds':4,'dimensions':[1080,1080],'codec':'H264','audio':False,'faststart':f,'bytes':os.path.getsize(path),'sha256':sha(path),'engine':'BLENDER_EEVEE_NEXT','samples':64}

# Garlic full video first, sequentially. Samples remain native material renders.
open_blend(garlic_blend);hd_settings('Garlic',[0,12,36,60,84]);render_still(os.path.join(OUT,'previews','Garlic_1080p_hop.png'),12);render_still(os.path.join(OUT,'previews','Garlic_1080p_tilt.png'),36)
videos=[direct_video('Garlic','Garlic_body_motion_1080p.mp4',0)];dump('video_progress.json',videos);print('GARLIC HD VIDEO CREATED',flush=True)
open_blend(os.path.join(OUT,'models','Ginger_rigged.blend'));hd_settings('Ginger',[1,7,13,19,25]);rig=bpy.data.objects['Ginger_Rig'];clip=rig.animation_data.action.copy();clip.name='Ginger_HD_render_loop_only';rig.animation_data.action=clip
for fc in clip.fcurves:
    for kp in fc.keyframe_points:
        kp.co.x=(kp.co.x-1)*2;kp.handle_left.x=(kp.handle_left.x-1)*2;kp.handle_right.x=(kp.handle_right.x-1)*2
    fc.modifiers.new('CYCLES')
render_still(os.path.join(OUT,'previews','Ginger_1080p_arms.png'),12);render_still(os.path.join(OUT,'previews','Ginger_1080p_legs.png'),24)
videos.append(direct_video('Ginger','Ginger_FK_motion_1080p.mp4',0));dump('video_progress.json',videos);print('GINGER HD VIDEO CREATED',flush=True)

# Actually decode the produced MP4s through Blender's built-in movie reader.
for row in videos:
    bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.render.fps=24;s.render.resolution_x=s.render.resolution_y=1080;s.render.resolution_percentage=100;s.render.threads_mode='FIXED';s.render.threads=2;ed=s.sequence_editor_create();movie=ed.sequences.new_movie(name='Actual final H264 decode',filepath=os.path.join(OUT,row['file']),channel=1,frame_start=0)
    assert movie.frame_duration==96 and movie.elements[0].orig_width==1080 and movie.elements[0].orig_height==1080
    s.render.use_sequencer=True;s.render.use_compositing=False;s.view_settings.view_transform='Standard';s.view_settings.look='None';s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGB'
    for f in [0,12,36]:s.frame_set(f);s.render.filepath=os.path.join(AUD,os.path.basename(row['file'])+'_decoded_%03d.png'%f);bpy.ops.render.render(write_still=True)
    row['actual_movie_decode']={'frames':96,'dimensions':[1080,1080],'sample_frames':[0,12,36]}
for folder,n in [('models','Ginger_rigged.blend'),('models','Garlic_rigged.blend'),('glb','Ginger_rigged.glb'),('glb','Garlic_rigged.glb')]:assert sha(os.path.join(SRC,folder,n))==source_hashes[n]
assert sha(os.path.join(OUT,'models','Ginger_rigged.blend'))==source_hashes['Ginger_rigged.blend'];assert sha(os.path.join(OUT,'glb','Ginger_rigged.glb'))==source_hashes['Ginger_rigged.glb']
dump('hd_revision_verification.json',{'garlic_native':native_report,'garlic_glb':glb_report,'ginger_bytecopies_unchanged':True,'source_v1_1_0_models_glb_unchanged':True,'source_hashes':source_hashes,'videos':videos,'render_limitations':'GLB retains v1.1.0 baked PBR/vertex-color approximation; canonical blend and HD movies use unchanged approved material graphs.'})
print('HD REVISION COMPLETE - SOURCES UNCHANGED',flush=True)
