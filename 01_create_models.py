"""Own procedural geometry, seeded pencil textures, FK rigs and clips.

Blender 4.3.2: blender --factory-startup --background --threads 2 --python create_source.py -- --out OUTPUT --audit AUDIT
Visual reference silhouettes were inspected manually. No reference JPG, existing model,
texture, atlas, font or motion file is read by this generator.
The owner explicitly authorizes CC0-1.0 for the entire independently generated model,
including mesh, materials, textures, rig, test animation and code. Commercial use,
modification and redistribution are permitted. Reference JPGs are not embedded.
"""
import bpy,math,random,os,json,hashlib,array,argparse,sys,struct,time
from mathutils import Vector,Quaternion

argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
p=argparse.ArgumentParser();p.add_argument('--out',default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))));p.add_argument('--audit',default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'technical-audit'));p.add_argument('--only',choices=['Negi','Wasabi','Mustard']);args=p.parse_args(argv)
OUT=os.path.abspath(args.out);AUD=os.path.abspath(args.audit)
for d in ['models','glb','textures','previews','animations','docs']:os.makedirs(os.path.join(OUT,d),exist_ok=True)
os.makedirs(AUD,exist_ok=True)

def blend(a,b,t):return tuple(a[i]*(1-t)+b[i]*t for i in range(3))
def smooth(a,b,x):
    t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
def texture(name,kind,color=None,size=256,seed=1729):
    rng=random.Random(seed);im=bpy.data.images.new(name,width=size,height=size,alpha=True);im.colorspace_settings.name='sRGB';pixels=array.array('f')
    for j in range(size):
        v=j/(size-1)
        for i in range(size):
            u=i/(size-1)
            if kind=='negi':
                rgb=blend((.95,.95,.88),(.55,.70,.46),smooth(.46,.92,v));rgb=tuple(c+.012*math.sin(u*70+v*4)*smooth(.48,.85,v) for c in rgb)
            elif kind=='wasabi':
                rgb=(.65,.80,.56);patch=.030*math.sin(u*14+math.sin(v*11))*math.cos(v*26)+.013*math.sin(v*51)
                rgb=tuple(c+patch for c in rgb)
            elif kind=='mustard':
                rgb=(.95,.86,.43)
                if .725<v<.790 or .834<v<.893:rgb=(.91,.43,.19)
                if .935<v<.945 and math.sin(u*100)>.0:rgb=(.57,.41,.22)
            else:rgb=color
            # Independent pencil/paper grain and faint diagonal/vertical hatch; no image pixels are sampled.
            grain=rng.uniform(-.017,.017)
            hatch=-.012*(max(0,math.sin((u*1.7+v)*size*1.12))**12)
            broad=.004*math.sin(u*19+v*23)+.003*math.cos(u*39-v*13)
            pixels.extend([max(0,min(1,c+grain+hatch+broad)) for c in rgb]+[1])
    im.pixels.foreach_set(pixels);im.file_format='PNG';file=name+'.png';im.filepath_raw=os.path.join(OUT,'textures',file);im.save();im.pack();im.filepath='//../textures/'+file
    for packed in im.packed_files:packed.filepath='//../textures/'+file
    return im

def material(name,image):
    m=bpy.data.materials.new(name);m.use_nodes=True;nt=m.node_tree;b=nt.nodes.get('Principled BSDF');b.inputs['Roughness'].default_value=.88;b.inputs['Metallic'].default_value=0
    tex=nt.nodes.new('ShaderNodeTexImage');tex.name='Own seeded pencil texture';tex.image=image;nt.links.new(tex.outputs['Color'],b.inputs['Base Color'])
    return m

def create_materials(prefix):
    mats={}
    mats['body']=material(prefix+' own pencil body',texture(prefix+'_pencil_body',prefix.lower(),size=512,seed={'Negi':101,'Wasabi':202,'Mustard':303}[prefix]))
    colors={'cocoa':(.43,.285,.18),'white':(.98,.98,.92),'pink':(.93,.54,.59),'red':(.86,.30,.23),'orange':(.95,.39,.15),'leaf':(.59,.74,.41),'cut':(.66,.78,.53),'hand':(.94,.94,.87) if prefix=='Negi' else ((.65,.80,.56) if prefix=='Wasabi' else (.95,.86,.43)),'cap':(.94,.84,.43)}
    for n,col in colors.items():mats[n]=material(prefix+' own pencil '+n,texture(prefix+'_pencil_'+n,'solid',col,size=128,seed=400+sum(map(ord,prefix+n))))
    return mats

def uv_project(o,mode='xz',scale=None):
    uv=o.data.uv_layers.new(name='UVMap') if not o.data.uv_layers else o.data.uv_layers[0]
    coords=[v.co for v in o.data.vertices];xmin=min(v.x for v in coords);xmax=max(v.x for v in coords);zmin=min(v.z for v in coords);zmax=max(v.z for v in coords)
    for loop in o.data.loops:
        v=o.data.vertices[loop.vertex_index].co
        if scale=='Negi':u=(v.x+.55)/1.0;w=v.z/2.48
        elif scale=='Wasabi':u=(v.x+.55)/1.1;w=v.z/2.45
        elif scale=='Mustard':u=(v.x+.9)/1.6;w=(v.z-.22*v.x)/2.5
        else:u=(v.x-xmin)/max(1e-5,xmax-xmin);w=(v.z-zmin)/max(1e-5,zmax-zmin)
        uv.data[loop.index].uv=(u,w)

def mesh(name,verts,faces,mat,collection=None,smooth_faces=False,uv_scale=None):
    data=bpy.data.meshes.new(name+' math mesh');data.from_pydata(verts,[],faces);data.update();o=bpy.data.objects.new(name,data);(collection or bpy.context.scene.collection).objects.link(o);o.data.materials.append(mat)
    for f in data.polygons:f.use_smooth=smooth_faces
    uv_project(o,scale=uv_scale);return o

def catmull(points,steps=6,closed=False):
    a=[Vector(p) for p in points];out=[];n=len(a)
    for i in range(n if closed else n-1):
        p0=a[(i-1)%n] if closed or i>0 else a[0];p1=a[i];p2=a[(i+1)%n];p3=a[(i+2)%n] if closed or i+2<n else a[-1]
        for j in range(steps):
            t=j/steps;out.append(tuple(.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t)))
    if not closed:out.append(tuple(a[-1]))
    return out

def tube(name,points,radius,mat,closed=False,collection=None,segments=8):
    pts=[Vector(x) for x in points];verts=[];n=len(pts)
    for i,c in enumerate(pts):
        prev=pts[(i-1)%n] if closed or i>0 else pts[0];nxt=pts[(i+1)%n] if closed or i<n-1 else pts[-1];axis=(nxt-prev).normalized();side=axis.cross(Vector((0,-1,0))).normalized()
        if side.length<.01:side=axis.cross(Vector((1,0,0))).normalized()
        second=axis.cross(side).normalized();r=radius*(.97+.03*math.sin(i*.73))
        for j in range(segments):
            t=2*math.pi*j/segments;verts.append(tuple(c+r*(side*math.cos(t)+second*math.sin(t))))
    faces=[]
    for i in range(n if closed else n-1):
        for j in range(segments):faces.append((i*segments+j,i*segments+(j+1)%segments,((i+1)%n)*segments+(j+1)%segments,((i+1)%n)*segments+j))
    if not closed:faces.extend([tuple(reversed(range(segments))),tuple((n-1)*segments+j for j in range(segments))])
    o=mesh(name,verts,faces,mat,collection,smooth_faces=True);o.visible_shadow=False;return o

def extrusion(name,outline,depth,mat,prefix,bevel=.035):
    pts=catmull(outline,5,True);n=len(pts);verts=[(x,-depth,z) for x,z in pts]+[(x,depth,z) for x,z in pts]
    faces=[tuple(reversed(range(n))),tuple(n+i for i in range(n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    o=mesh(name,verts,faces,mat,uv_scale=prefix)
    if bevel:
        mod=o.modifiers.new('Own rounded edge','BEVEL');mod.width=bevel;mod.segments=3
    return o,pts

def ellipse(name,cx,cz,rx,rz,y,mat,outline=None,tilt=0):
    verts=[(cx,y,cz)];n=48
    pts=[]
    for i in range(n):
        t=2*math.pi*i/n;x=cx+rx*math.cos(t);z=cz+rz*math.sin(t)+tilt*(x-cx);pts.append((x,y,z));verts.append((x,y,z))
    faces=[(0,1+i,1+(i+1)%n) for i in range(n)];o=mesh(name,verts,faces,mat);o.visible_shadow=False
    if outline:tube(name+' cocoa contour',pts,.011,outline,closed=True)
    return o

def filled_shape(name,points,y,mat,outline=None,radius=.014):
    pts=catmull(points,5,True);verts=[(x,y,z) for x,z in pts]
    signed=sum(pts[i][0]*pts[(i+1)%len(pts)][1]-pts[(i+1)%len(pts)][0]*pts[i][1] for i in range(len(pts)))
    face=tuple(range(len(verts))) if signed>0 else tuple(reversed(range(len(verts))))
    o=mesh(name,verts,[face],mat);o.visible_shadow=False
    if outline:tube(name+' cocoa contour',verts,radius,outline,closed=True)
    return o

def cut_disk(name,center,rx,ry,mat,rim):
    c=Vector(center);u=Vector((1,0,.20));v=Vector((0,1,.15));pts=[tuple(c+rx*math.cos(2*math.pi*i/48)*u+ry*math.sin(2*math.pi*i/48)*v) for i in range(48)]
    mesh(name,[tuple(c)]+pts,[(0,1+i,1+(i+1)%48) for i in range(48)],mat);tube(name+' brown cut rim',pts,.014,rim,True)

def sphere(name,center,scale,mat,collection=None):
    n=20;rings=12;verts=[]
    for i in range(rings+1):
        a=math.pi*i/rings
        for j in range(n):
            b=2*math.pi*j/n;verts.append((center[0]+scale[0]*math.sin(a)*math.cos(b),center[1]+scale[1]*math.sin(a)*math.sin(b),center[2]+scale[2]*math.cos(a)))
    faces=[]
    for i in range(rings):
        for j in range(n):faces.append(tuple(reversed((i*n+j,i*n+(j+1)%n,(i+1)*n+(j+1)%n,(i+1)*n+j))))
    return mesh(name,verts,faces,mat,collection,smooth_faces=True)

def stem(name,start,end,radius,mat,rim):
    a=Vector(start);b=Vector(end);d=(b-a).normalized();u=d.cross(Vector((0,1,0))).normalized();v=d.cross(u).normalized();verts=[];segments=24
    for row in range(9):
        t=row/8;c=a.lerp(b,t);r=radius*(.90+.10*t)
        for j in range(segments):
            ph=2*math.pi*j/segments;verts.append(tuple(c+r*(math.cos(ph)*u+math.sin(ph)*v)))
    faces=[]
    for k in range(8):
        for j in range(segments):faces.append((k*segments+j,k*segments+(j+1)%segments,(k+1)*segments+(j+1)%segments,(k+1)*segments+j))
    faces.extend([tuple(reversed(range(segments))),tuple(8*segments+i for i in range(segments))]);o=mesh(name,verts,faces,mat,smooth_faces=True)
    cap=[tuple(b+radius*(math.cos(2*math.pi*i/segments)*u+math.sin(2*math.pi*i/segments)*v)) for i in range(segments)];tube(name+' cut rim',cap,.011,rim,True)
    for side in [-1,1]:tube(name+' outline '+str(side),[tuple(a+side*radius*.90*u+Vector((0,-radius*.72,0))),tuple(b+side*radius*u+Vector((0,-radius*.72,0)))],.010,rim)
    return o

def negi(m):
    # Continuous S-shaped white stalk with a real fork-shaped silhouette, taller left cut.
    profile=[(-.50,.16),(-.39,.36),(-.27,.66),(-.17,.96),(-.085,1.28),(-.09,1.46),(-.25,1.94),(-.40,2.33),(-.33,2.38),(-.12,2.44),(.075,2.38),(.13,1.87),(.18,1.46),(.18,1.82),(.16,2.17),(.26,2.23),(.39,2.21),(.40,1.85),(.40,1.47),(.42,1.21),(.38,.93),(.28,.58),(.14,.045),(-.16,.07)]
    body,pts=extrusion('Negi curved two-cut continuous stalk',profile,.155,m['body'],'Negi',.025)
    tube('Negi original silhouette brown pencil contour',[(x,-.166,z) for x,z in pts],.013,m['cocoa'],True)
    cut_disk('Negi taller left cut',(-.16,-.01,2.382),.242,.144,m['cut'],m['cocoa'])
    cut_disk('Negi shorter right cut',(.288,-.005,2.218),.139,.13,m['cut'],m['cocoa'])
    facey=-.192
    for suffix,x in [('L',-.12),('R',.13)]:
        ellipse('Negi oval eye.'+suffix,x,.645,.071,.126,facey,m['cocoa'])
        ellipse('Negi white eye light.'+suffix,x-.006,.707,.029,.028,facey-.007,m['white'])
    tube('Negi short steep left eyebrow',[(x,facey,z) for x,z in catmull([(-.165,.94),(-.143,.886),(-.095,.851)],5)],.017,m['cocoa'])
    tube('Negi longer angled right eyebrow',[(x,facey,z) for x,z in catmull([(.075,.853),(.155,.893),(.229,.928)],5)],.015,m['cocoa'])
    filled_shape('Negi pink open smile',[(-.14,.467),(-.06,.432),(.09,.467),(.08,.384),(.005,.342),(-.068,.385)],facey-.004,m['pink'],m['cocoa'],.015)
    return body,{'arm_z':.57,'arm_pivots':[-.30,.27],'leg_x':[-.25,.07],'leg_z':.095}

def wasabi(m):
    # Nine slightly unequal knuckles and a root axis leaning right toward the bottom.
    left=[];right=[]
    for i in range(37):
        z=.09+1.88*i/36;c=.18-.40*(z/1.97);r=.31+.035*math.sin(i*math.pi/2+.4)+.014*math.sin(i*1.1)
        taper=.82+.18*math.sin(math.pi*i/36)**.5;r*=taper
        left.append((c-r,z));right.append((c+r+.018*math.sin(i*.9),z))
    profile=left+list(reversed(right));body,pts=extrusion('Wasabi segmented leaning rhizome',profile,.245,m['body'],'Wasabi',.05)
    tube('Wasabi wavy original contour',[(x,-.257,z) for x,z in pts],.014,m['cocoa'],True)
    for index,a,b,r in [(1,(-.30,.075,1.93),(-.435,.075,2.27),.080),(2,(-.13,.09,1.96),(-.16,.09,2.29),.080),(3,(-.22,-.025,1.91),(-.31,-.025,2.45),.105),(4,(.00,-.045,1.94),(.125,-.045,2.45),.112)]:
        stem('Wasabi cut leaf stem '+str(index),a,b,r,m['leaf'],m['cocoa'])
    fy=-.285
    for suffix,x in [('L',-.14),('R',.145)]:
        ellipse('Wasabi horizontal brown eye.'+suffix,x,1.065,.114,.085,fy,m['cocoa'])
        ellipse('Wasabi left-side white highlight.'+suffix,x-.044,1.075,.033,.048,fy-.007,m['white'])
    ellipse('Wasabi small red oval mouth',.024,.878,.083,.043,fy-.005,m['red'],m['cocoa'])
    return body,{'arm_z':.77,'arm_pivots':[-.30,.35],'leg_x':[-.04,.26],'leg_z':.10}

def mustard(m):
    profile=[(-.865,2.30),(-.47,2.407),(.095,2.545),(.075,2.24),(.18,1.84),(.26,1.46),(.38,1.04),(.52,.62),(.60,.335),(.52,.292),(.553,.083),(.388,.036),(.315,.232),(.190,.202),(.035,.455),(-.17,.86),(-.37,1.34),(-.57,1.85)]
    body,pts=extrusion('Mustard flattened tapered tube and short nozzle',profile,.115,m['body'],'Mustard',.025)
    tube('Mustard original tube brown pencil contour',[(x,-.132,z) for x,z in pts],.014,m['cocoa'],True)
    fy=-.151
    for suffix,x,z in [('L',-.15,1.35),('R',.16,1.41)]:
        points=[]
        for i in range(25):
            t=math.pi*i/24;points.append((x+.084*math.cos(t),fy,z+.138*math.sin(t)))
        tube('Mustard closed happy arc eye.'+suffix,points,.019,m['cocoa'])
    filled_shape('Mustard vermilion open smiling mouth',[(-.19,1.239),(.185,1.303),(.171,1.132),(.045,1.080),(-.108,1.118)],fy-.003,m['orange'],m['cocoa'],.018)
    # Optional cap is an accessory, never a leg. Default hidden for the primary character preview.
    caps=bpy.data.collections.new('OPTIONAL PROPS - cap and mustard dab (off by default)');bpy.context.scene.collection.children.link(caps)
    c=(-.45,0,-.21);cap=sphere('Mustard optional rounded cap',c,(.13,.115,.14),m['cap'],caps)
    for i in range(8):
        theta=2*math.pi*i/8;x=c[0]+.127*math.cos(theta);y=c[1]+.115*math.sin(theta)
        tube('Mustard optional cap rib '+str(i),[(x,y,-.31),(x,y,-.12)],.005,m['cocoa'],collection=caps)
    dabpoints=catmull([(.69,0,-.125),(.765,0,-.235),(.89,0,-.30),(1.04,0,-.33),(1.14,0,-.285)],6)
    tube('Mustard optional squeezed dab',dabpoints,.065,m['cap'],collection=caps,segments=12)
    caps.hide_render=True;caps.hide_viewport=True
    return body,{'arm_z':.73,'arm_pivots':[-.12,.47],'leg_x':[.20,.46],'leg_z':.25}

def make_rig(prefix,m,config):
    original=[o for o in bpy.data.objects if o.type=='MESH'];arm=bpy.data.armatures.new(prefix+' own FK bones');rig=bpy.data.objects.new(prefix+'_Rig',arm);bpy.context.scene.collection.objects.link(rig)
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT')
    def bone(name,h,t,parent=None):
        b=arm.edit_bones.new(name);b.head=h;b.tail=t
        if parent:b.parent=arm.edit_bones[parent]
    bone('root',(0,0,-.10),(0,0,.08));bone('body',(0,0,.10),(0,0,1.7),'root')
    for i,suffix in enumerate(['L','R']):
        sign=-1 if i==0 else 1;x=config['arm_pivots'][i];z=config['arm_z'];bone('arm.'+suffix,(x,0,z),(x+sign*.19,0,z-.03),'body')
        x=config['leg_x'][i];z=config['leg_z'];bone('leg.'+suffix,(x,0,z),(x,0,z-.19),'root')
    bpy.ops.object.mode_set(mode='OBJECT')
    coll=bpy.data.collections.new('ADDED ROUNDED LIMBS - toggle viewport and render');bpy.context.scene.collection.children.link(coll)
    limbs=[]
    for i,suffix in enumerate(['L','R']):
        sign=-1 if i==0 else 1;x=config['arm_pivots'][i];z=config['arm_z'];o=sphere(prefix+' added arm.'+suffix,(x+sign*.13,0,z-.025),(.13,.075,.074),m['hand'],coll);limbs.append((o,'arm.'+suffix))
        x=config['leg_x'][i];z=config['leg_z'];o=sphere(prefix+' added leg.'+suffix,(x,-.01,z-.115),(.072,.088,.120),m['hand'],coll);limbs.append((o,'leg.'+suffix))
    for o,bname in [(o,'body') for o in original]+limbs:
        g=o.vertex_groups.new(name=bname);g.add(list(range(len(o.data.vertices))),1,'REPLACE');mod=o.modifiers.new('Own FK skin weights','ARMATURE');mod.object=rig;mod.use_deform_preserve_volume=True;o.parent=rig
    rig.show_in_front=True;arm.display_type='STICK'
    for b in rig.pose.bones:
        b.rotation_mode='XYZ';b.lock_scale=(True,)*3
        if b.name not in ['root','body']:b.lock_location=(True,)*3
        if b.name.startswith(('arm.','leg.')):
            c=b.constraints.new('LIMIT_ROTATION');c.name='Gentle FK range';c.owner_space='LOCAL';c.use_limit_x=c.use_limit_y=c.use_limit_z=True;lim=math.radians(35 if b.name.startswith('arm.') else 22);c.min_x=c.min_y=c.min_z=-lim;c.max_x=c.max_y=c.max_z=lim
        b.bone.color.palette='THEME04' if b.name.startswith('arm.') else ('THEME03' if b.name.startswith('leg.') else 'THEME01')
    rig['asset_license']='CC0-1.0: Owner explicitly permits commercial use, modification and redistribution of this independently generated model, including mesh/material/texture/rig/animation/code.';rig['front_direction']='-Y; Z up';rig['controls']='root/body/arm.L/arm.R/leg.L/leg.R; see docs/RIG_USAGE.md'
    return rig,coll

def pose_angle(rig,name,angle):
    axis=rig.data.bones[name].matrix_local.to_quaternion().inverted()@Vector((0,1,0));return Quaternion(axis,angle).to_euler('XYZ')
def action(prefix,rig):
    a=bpy.data.actions.new(prefix+'_FK_motion_check');a.use_fake_user=True;rig.animation_data_create();rig.animation_data.action=a;s=bpy.context.scene;s.render.fps=12;s.frame_start=1;s.frame_end=25
    for frame,armval,legval in [(1,0,0),(7,1,0),(13,0,1),(19,-.5,-1),(25,0,0)]:
        for b in rig.pose.bones:b.rotation_euler=(0,0,0)
        for suffix,sign in [('L',-1),('R',1)]:
            rig.pose.bones['arm.'+suffix].rotation_euler=pose_angle(rig,'arm.'+suffix,math.radians(25)*armval*sign)
            rig.pose.bones['leg.'+suffix].rotation_euler=pose_angle(rig,'leg.'+suffix,math.radians(15)*legval*sign)
        for b in rig.pose.bones:b.keyframe_insert('rotation_euler',frame=frame,group=b.name)
    for f in a.fcurves:
        for k in f.keyframe_points:k.interpolation='BEZIER'
    for frame,label in [(1,'Rest'),(7,'Arms'),(13,'Legs'),(19,'Arms and legs'),(25,'Loop rest')]:s.timeline_markers.new(label,frame=frame)
    s.frame_set(1);return a

def setup_camera(prefix):
    s=bpy.context.scene;coll=bpy.data.collections.new('PREVIEW lights and camera');s.collection.children.link(coll);target=Vector((-.03,0,1.14));cd=bpy.data.cameras.new('Preview camera');o=bpy.data.objects.new('Preview camera',cd);coll.objects.link(o);o.location=(0,-8,2.4);o.rotation_euler=(target-o.location).to_track_quat('-Z','Y').to_euler();cd.type='ORTHO';cd.ortho_scale=3.15;s.camera=o
    for name,pos,power,size in [('Key',(-3,-4,5),500,4),('Fill',(3,-3,3),350,4),('Rim',(0,3,4),200,3)]:
        ld=bpy.data.lights.new(name,'AREA');ld.energy=power;ld.size=size;light=bpy.data.objects.new(name,ld);coll.objects.link(light);light.location=pos;light.rotation_euler=(target-light.location).to_track_quat('-Z','Y').to_euler()
    s.world=bpy.data.worlds.new('Own neutral preview world');s.world.use_nodes=True;s.world.node_tree.nodes.get('Background').inputs['Strength'].default_value=.35
    s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=8;s.cycles.use_denoising=False;s.render.threads_mode='FIXED';s.render.threads=2;s.render.film_transparent=True;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';s.view_settings.view_transform='Standard';s.view_settings.look='None'

def render(path,size=384,samples=8):
    s=bpy.context.scene;s.render.resolution_x=s.render.resolution_y=size;s.render.resolution_percentage=100;s.cycles.samples=samples;s.render.filepath=path;bpy.ops.render.render(write_still=True)
def positions():
    bpy.context.view_layer.update();d=bpy.context.evaluated_depsgraph_get();r={}
    for o in bpy.data.objects:
        if o.type!='MESH' or o.hide_render:continue
        e=o.evaluated_get(d);m=e.to_mesh();r[o.name]=[e.matrix_world@v.co for v in m.vertices];e.to_mesh_clear()
    return r
def changes(a,b):return {n:max(((x-y).length for x,y in zip(a[n],p)),default=0) for n,p in b.items()}

def export(prefix):
    bpy.ops.object.select_all(action='DESELECT')
    for o in bpy.data.objects:
        if o.type in ['MESH','ARMATURE'] and not any(c.hide_render for c in o.users_collection):o.select_set(True)
    props={p.identifier for p in bpy.ops.export_scene.gltf.get_rna_type().properties}
    opt={'filepath':os.path.join(OUT,'glb',prefix+'_rigged.glb'),'export_format':'GLB','use_selection':True,'export_animations':True,'export_animation_mode':'ACTIONS','export_skins':True,'export_yup':True,'export_apply':True,'export_extras':False,'export_normals':True,'export_texcoords':True,'export_materials':'EXPORT','export_frame_range':True,'export_frame_step':1,'export_force_sampling':True,'export_image_format':'AUTO'};bpy.ops.export_scene.gltf(**{k:v for k,v in opt.items() if k in props})

def build(prefix):
    started=time.monotonic();bpy.ops.wm.read_factory_settings(use_empty=True);m=create_materials(prefix);body,cfg={'Negi':negi,'Wasabi':wasabi,'Mustard':mustard}[prefix](m);rig,limbs=make_rig(prefix,m,cfg);a=action(prefix,rig);setup_camera(prefix)
    s=bpy.context.scene;rest=positions();s.frame_set(7);arms=changes(rest,positions());s.frame_set(13);legs=changes(rest,positions());assert arms[prefix+' added arm.L']>1e-4 and arms[prefix+' added arm.R']>1e-4;assert legs[prefix+' added leg.L']>1e-4 and legs[prefix+' added leg.R']>1e-4
    for o in bpy.data.objects:
        if o.type=='MESH':assert all(abs(sum(g.weight for g in v.groups)-1)<1e-6 for v in o.data.vertices)
    s.frame_set(1);limbs.hide_render=True;render(os.path.join(OUT,'previews',prefix+'_reference_form.png'));limbs.hide_render=False;render(os.path.join(OUT,'previews',prefix+'_rigged_rest.png'))
    if prefix=='Mustard':
        props=bpy.data.collections['OPTIONAL PROPS - cap and mustard dab (off by default)'];props.hide_render=False;props.hide_viewport=False
        limbs.hide_render=True;render(os.path.join(OUT,'previews',prefix+'_reference_with_props.png'));limbs.hide_render=False
        props.hide_render=True;props.hide_viewport=True
    s.frame_set(7);render(os.path.join(OUT,'previews',prefix+'_rigged_arms.png'));s.frame_set(13);render(os.path.join(OUT,'previews',prefix+'_rigged_legs.png'))
    s.frame_set(1);s.render.filepath='//../previews/'+prefix+'_rigged_rest.png';s.render.resolution_x=s.render.resolution_y=384;s.cycles.samples=8
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig;bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,'models',prefix+'_rigged.blend'),check_existing=False,compress=True,relative_remap=False)
    export(prefix)
    frames=os.path.join(AUD,prefix+'_frames');os.makedirs(frames,exist_ok=True)
    for f in range(1,25):s.frame_set(f);render(os.path.join(frames,'%03d.png'%f),256,4)
    s.frame_set(1)
    meshrows=[{'name':o.name,'vertices':len(o.data.vertices),'polygons':len(o.data.polygons),'weight_groups':[g.name for g in o.vertex_groups]} for o in bpy.data.objects if o.type=='MESH']
    texrows=[{'name':i.name,'filepath':i.filepath,'packed':bool(i.packed_file),'source':i.source,'sha256':hashlib.sha256(i.packed_file.data).hexdigest() if i.packed_file else None} for i in bpy.data.images if i.name!='Render Result']
    report={'character':prefix,'geometry_origin':'Generated solely by this script from mathematical profiles, curves, ellipses and rounded parametric meshes; no existing model read','texture_origin':'Generated solely by seeded math/noise pencil palette, no input image sampled','reference_use':'Manually inspected front silhouette and face proportions; reference JPG not embedded or distributed','owner_authorization':'The owner explicitly authorizes CC0-1.0 for this independently generated model, including mesh/material/texture/rig/animation/code. Commercial use, modification and redistribution are permitted.','mesh_data':meshrows,'textures':texrows,'rig_bones':[b.name for b in rig.data.bones],'action':{'name':a.name,'fps':12,'frames':[1,25],'seconds':2},'arms_displacements':arms,'legs_displacements':legs,'creation_seconds':round(time.monotonic()-started,2)}
    with open(os.path.join(AUD,prefix+'_creation.json'),'w',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
    print('CREATED',prefix,flush=True)

if __name__=='__main__':
    for prefix in ['Negi','Wasabi','Mustard']:
        if not args.only or args.only==prefix:build(prefix)
