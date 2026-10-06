"""Own procedural geometry, seeded pencil textures, FK rigs and clips.

Blender 4.3.2: blender --factory-startup --background --threads 2 --python create_source.py -- --out OUTPUT --audit AUDIT
Visual reference silhouettes were inspected manually. No reference JPG, existing model,
texture, atlas, font or motion file is read by this generator.
CC0-1.0 applies to the complete generated model assets, materials, textures, rigs,
animations and technical source. Commercial use, modification and redistribution are permitted.
Original reference JPGs are private and are not copied into this package.
"""
import bpy,math,random,os,json,hashlib,array,argparse,sys,struct,time
from mathutils import Vector,Quaternion

argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
p=argparse.ArgumentParser();p.add_argument('--out',default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))));p.add_argument('--audit',default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'technical-audit'));p.add_argument('--only',choices=['Yuzu','Chili','Myoga']);args=p.parse_args(argv)
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
            elif kind=='yuzu':
                rgb=(.965,.871,.409);patch=.008*math.sin(u*11)*math.sin(v*17);rgb=tuple(c+patch for c in rgb)
            elif kind=='chili':
                rgb=(.929,.404,.480);patch=.016*math.sin(u*8+v*3)+.009*math.cos(v*9);rgb=tuple(c+patch for c in rgb)
            elif kind=='myoga':
                rgb=blend((.974,.942,.786),(.900,.400,.470),smooth(.20,.69,v));patch=.006*math.sin(u*53)*smooth(.22,.77,v);rgb=tuple(c+patch for c in rgb)
            elif kind=='myogaleaf':
                rgb=blend((.880,.500,.570),(.400,.640,.350),smooth(.70,.91,v))
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
    for packed in im.packed_files:packed.filepath='//../textures/'+file
    return im

def material(name,image):
    m=bpy.data.materials.new(name);m.use_nodes=True;nt=m.node_tree;b=nt.nodes.get('Principled BSDF');b.inputs['Roughness'].default_value=.88;b.inputs['Metallic'].default_value=0
    tex=nt.nodes.new('ShaderNodeTexImage');tex.name='Own seeded pencil texture';tex.image=image;nt.links.new(tex.outputs['Color'],b.inputs['Base Color'])
    return m

def uv_project(o,mode='xz',scale=None):
    uv=o.data.uv_layers.new(name='UVMap') if not o.data.uv_layers else o.data.uv_layers[0]
    coords=[v.co for v in o.data.vertices];xmin=min(v.x for v in coords);xmax=max(v.x for v in coords);zmin=min(v.z for v in coords);zmax=max(v.z for v in coords)
    for loop in o.data.loops:
        v=o.data.vertices[loop.vertex_index].co
        if scale=='Negi':u=(v.x+.55)/1.0;w=v.z/2.48
        elif scale=='Wasabi':u=(v.x+.55)/1.1;w=v.z/2.45
        elif scale=='Mustard':u=(v.x+.9)/1.6;w=(v.z-.22*v.x)/2.5
        elif scale=='Yuzu':u=(v.x+.86)/1.72;w=(v.z-.25)/1.17
        elif scale=='Chili':u=(v.x+.74)/1.33;w=(v.z-.23)/2.38
        elif scale=='Myoga':u=(v.x+.50)/1.0;w=(v.z-.15)/2.52
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

def create_materials(prefix):
    mats={}
    seed={'Yuzu':504,'Chili':605,'Myoga':706}[prefix]
    mats['body']=material(prefix+' own pencil body',texture(prefix+'_pencil_body',prefix.lower(),size=512,seed=seed))
    colors={'cocoa':(.43,.285,.18),'white':(.98,.98,.92),'pink':(.93,.54,.59),'red':(.86,.30,.23),'leaf':(.46,.66,.36),'cut':(.84,.88,.62),'eyebrow':(.72,.65,.29),'cheek':(.48,.45,.22),'hand':{'Yuzu':(.96,.87,.40),'Chili':(.93,.40,.47),'Myoga':(.96,.89,.73)}[prefix]}
    for n,col in colors.items():mats[n]=material(prefix+' own pencil '+n,texture(prefix+'_pencil_'+n,'solid',col,size=128,seed=seed+sum(map(ord,n))))
    mats['leafpink']=material(prefix+' own pencil leaf pink',texture(prefix+'_pencil_leafpink','myogaleaf',size=256,seed=seed+81))
    return mats

def loft(name,rows,mat,prefix,segments=48):
    verts=[]
    for j,(z,cx,rx,ry) in enumerate(rows):
        for i in range(segments):
            a=2*math.pi*i/segments
            # The silhouette has subtle own-authored pencil irregularity.
            wobble=1+.007*math.sin(7*a+j*.72)+.004*math.sin(13*a+j*.45)
            verts.append((cx+rx*math.cos(a)*wobble,ry*math.sin(a)*wobble,z))
    faces=[tuple(reversed(range(segments)))]
    for j in range(len(rows)-1):
        for i in range(segments):faces.append((j*segments+i,j*segments+(i+1)%segments,(j+1)*segments+(i+1)%segments,(j+1)*segments+i))
    faces.append(tuple((len(rows)-1)*segments+i for i in range(segments)))
    return mesh(name,verts,faces,mat,smooth_faces=True,uv_scale=prefix)

def yuzu(m):
    rows=[(.27,0,.32,.14),(.30,0,.56,.21),(.37,-.005,.75,.29),(.52,-.005,.835,.355),(.72,0,.83,.37),(.90,0,.77,.35),(1.08,-.005,.66,.31),(1.24,-.005,.51,.26),(1.35,-.015,.33,.185),(1.40,-.02,.12,.085),(1.405,-.02,.005,.005)]
    body=loft('Yuzu squat gently dimpled fruit',rows,m['body'],'Yuzu')
    outline=[(-.32,.267),(-.60,.302),(-.78,.399),(-.842,.600),(-.815,.82),(-.686,1.062),(-.513,1.241),(-.304,1.367),(-.02,1.42),(.304,1.36),(.513,1.24),(.686,1.06),(.81,.82),(.842,.60),(.78,.399),(.60,.302),(.32,.267)]
    # Slightly forward cocoa contour follows the rim rather than darkening the face.
    pts=catmull(outline,5,True);tube('Yuzu soft cocoa silhouette',[(x,-.047,z) for x,z in pts],.017,m['cocoa'],True)
    fy=-.377
    for suffix,x,z in [('L',-.245,.661),('R',.247,.647)]:
        ellipse('Yuzu round brown eye.'+suffix,x,z,.117,.122,fy,m['cocoa'])
        ellipse('Yuzu white eye light.'+suffix,x-.019,z+.039,.037,.039,fy-.009,m['white'])
    for suffix,points in [('L',[(-.338,.894),(-.27,.908),(-.196,.900)]),('R',[(.174,.899),(.239,.887),(.306,.865)])]:
        tube('Yuzu gentle light eyebrow.'+suffix,[(x,fy+.009,z) for x,z in catmull(points,5)],.016,m['eyebrow'])
    tube('Yuzu w-shaped smiling mouth',[(x,fy-.004,z) for x,z in catmull([(-.146,.487),(-.133,.433),(-.075,.428),(0,.463),(.065,.421),(.122,.437),(.140,.483)],5)],.018,m['cocoa'])
    for sign in [-1,1]:
        for i,(dx,dz,r) in enumerate([(.0,.0,.014),(.051,.041,.012),(.086,-.022,.014),(-.012,-.055,.011),(.073,-.076,.010)]):
            ellipse('Yuzu own pencil cheek fleck '+str(sign)+' '+str(i),sign*(.423+dx),.525+dz,r,r*1.15,fy+.009,m['cheek'])
    filled_shape('Yuzu small recessed stem mark',[(-.144,1.278),(-.123,1.207),(-.015,1.185),(.103,1.224),(.091,1.278)],-.305,m['cut'],m['cocoa'],.016)
    return body,{'arm_z':.52,'arm_pivots':[-.797,.787],'leg_x':[-.34,.34],'leg_z':.285}

def chili(m):
    rows=[(.23,-.72,.010,.009),(.28,-.65,.073,.049),(.37,-.54,.129,.085),(.52,-.37,.183,.121),(.72,-.21,.216,.150),(.94,-.025,.239,.164),(1.16,.12,.254,.179),(1.38,.23,.251,.180),(1.60,.292,.236,.176),(1.81,.326,.219,.172),(1.99,.33,.228,.167),(2.045,.33,.219,.143)]
    body=loft('Chili curved tapered red pod',rows,m['body'],'Chili')
    left=[(cx-r,z) for z,cx,r,d in rows];right=[(cx+r,z) for z,cx,r,d in rows]
    tube('Chili cocoa left curved rim',[(x,-.01,z) for x,z in catmull(left,5)],.015,m['cocoa'])
    tube('Chili cocoa right curved rim',[(x,-.01,z) for x,z in catmull(right,5)],.015,m['cocoa'])
    cut_disk('Chili small green cap',(.33,0,2.052),.224,.165,m['leaf'],m['cocoa'])
    stempts=catmull([(.32,0,2.035),(.392,0,2.17),(.422,0,2.34),(.452,0,2.58)],7)
    tube('Chili long gently curved green stem',stempts,.052,m['leaf'],segments=12)
    for sign in [-1,1]:tube('Chili stem brown edge '+str(sign),[(x+sign*.048,y-.01,z) for x,y,z in stempts],.009,m['cocoa'])
    fy=-.181
    tube('Chili angry slanted eye.L',[(x,fy,z) for x,z in catmull([(-.060,1.221),(-.024,1.165),(.009,1.106)],6)],.026,m['cocoa'])
    tube('Chili angry slanted eye.R',[(x,fy,z) for x,z in catmull([(.271,1.211),(.204,1.171),(.149,1.116)],6)],.026,m['cocoa'])
    tube('Chili small confident smile',[(x,fy-.005,z) for x,z in catmull([(-.096,1.007),(.001,.974),(.114,.976),(.212,1.004)],6)],.019,m['cocoa'])
    # At z=.845 (hand center) the pod sides are x=-.3340/.1242; pivots sit inside,
    # so the rounded arms overlap the actual curved mesh rather than float beside it.
    return body,{'arm_z':.87,'arm_pivots':[-.291,.098],'leg_x':[-.58,-.36],'leg_z':.45}

def myoga(m):
    profile=[(-.15,.15),(-.17,.37),(-.30,.57),(-.43,.87),(-.48,1.19),(-.46,1.44),(-.40,1.74),(-.29,2.03),(-.17,2.17),(-.025,2.05),(.12,2.14),(.24,2.28),(.285,2.04),(.36,1.78),(.425,1.44),(.465,1.14),(.405,.87),(.295,.58),(.175,.37),(.16,.15)]
    body,pts=extrusion('Myoga layered pink bud and pale root',profile,.208,m['body'],'Myoga',.028)
    tube('Myoga soft cocoa outer bud rim',[(x,-.22,z) for x,z in pts],.017,m['cocoa'],True)
    leaves=[('tall rear',[(-.245,1.81),(-.178,2.31),(.045,2.67),(.135,2.37),(.239,2.095),(.145,1.75)],.097,.075),('right rear',[(.015,1.84),(.185,2.25),(.484,2.43),(.410,2.15),(.349,1.865),(.115,1.59)],.025,.075),('left forward',[(-.200,1.69),(-.459,2.285),(-.100,2.175),(.126,1.946),(.208,1.653)],-.153,.080)]
    for title,outline,cy,depth in leaves:
        o,edge=extrusion('Myoga own pointed '+title+' leaf',outline,depth,m['leafpink'],'Myoga',.012);o.location.y=cy
        tube('Myoga '+title+' leaf cocoa edge',[(x,cy-depth-.008,z) for x,z in edge],.014,m['cocoa'],True)
    seam=catmull([(.21,.45),(.27,.85),(.253,1.21),(.10,1.55),(-.19,1.92),(-.385,2.15)],8)
    tube('Myoga long diagonal overlapping leaf seam',[(x,-.240,z) for x,z in seam],.016,m['cocoa'])
    fy=-.253
    for suffix,x,z in [('L',-.142,.856),('R',.121,.812)]:
        ellipse('Myoga warm brown oval eye.'+suffix,x,z,.077,.091,fy,m['cocoa'])
        ellipse('Myoga white eye glint.'+suffix,x-.012,z+.035,.027,.030,fy-.007,m['white'])
    for suffix,points in [('L',[(-.30,1.02),(-.23,.984),(-.18,1.035),(-.11,1.055),(-.058,1.029)]),('R',[(.045,.987),(.104,1.024),(.168,1.031),(.221,1.058)])]:
        tube('Myoga curved eyelash brow.'+suffix,[(x,fy,z) for x,z in catmull(points,5)],.020,m['cocoa'])
    for name,points in [('left outer',[(-.249,.997),(-.277,1.058)]),('right outer',[(.189,1.032),(.209,1.091)]),('right second',[(.154,1.028),(.175,1.090)])]:
        tube('Myoga eyelash '+name,[(x,fy,z) for x,z in points],.011,m['cocoa'])
    filled_shape('Myoga small open happy mouth',[(-.098,.646),(.030,.630),(.104,.595),(.062,.520),(-.010,.502),(-.065,.553)],fy-.004,m['white'],m['cocoa'],.016)
    return body,{'arm_z':.65,'arm_pivots':[-.300,.287],'leg_x':[-.10,.12],'leg_z':.155}

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
    rig['technical_data_license']='CC0-1.0; complete generated model, textures, rig, animation and code; commercial use/modification/redistribution permitted';rig['front_direction']='-Y; Z up';rig['controls']='root/body/arm.L/arm.R/leg.L/leg.R; see docs/RIG_USAGE.md'
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
    s=bpy.context.scene;coll=bpy.data.collections.new('PREVIEW lights and camera');s.collection.children.link(coll);target=Vector((0,0,.72 if prefix=='Yuzu' else 1.30));cd=bpy.data.cameras.new('Preview camera');o=bpy.data.objects.new('Preview camera',cd);coll.objects.link(o);o.location=(0,-8,2.4);o.rotation_euler=(target-o.location).to_track_quat('-Z','Y').to_euler();cd.type='ORTHO';cd.ortho_scale=2.50 if prefix=='Yuzu' else 3.15;s.camera=o
    for name,pos,power,size in [('Key',(-3,-4,5),500,4),('Fill',(3,-3,3),350,4),('Rim',(0,3,4),200,3)]:
        ld=bpy.data.lights.new(name,'AREA');ld.energy=power;ld.size=size;light=bpy.data.objects.new(name,ld);coll.objects.link(light);light.location=pos;light.rotation_euler=(target-light.location).to_track_quat('-Z','Y').to_euler()
    s.world=bpy.data.worlds.new('Own neutral preview world');s.world.use_nodes=True;s.world.node_tree.nodes.get('Background').inputs['Strength'].default_value=.35
    s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=32;s.cycles.use_denoising=False;s.render.threads_mode='FIXED';s.render.threads=2;s.render.film_transparent=True;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';s.view_settings.view_transform='Standard';s.view_settings.look='None'

def render(path,size=384,samples=32):
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
    started=time.monotonic();bpy.ops.wm.read_factory_settings(use_empty=True);m=create_materials(prefix);body,cfg={'Yuzu':yuzu,'Chili':chili,'Myoga':myoga}[prefix](m);rig,limbs=make_rig(prefix,m,cfg);a=action(prefix,rig);setup_camera(prefix)
    s=bpy.context.scene;rest=positions();s.frame_set(7);arms=changes(rest,positions());s.frame_set(13);legs=changes(rest,positions());assert arms[prefix+' added arm.L']>1e-4 and arms[prefix+' added arm.R']>1e-4;assert legs[prefix+' added leg.L']>1e-4 and legs[prefix+' added leg.R']>1e-4
    for o in bpy.data.objects:
        if o.type=='MESH':assert all(abs(sum(g.weight for g in v.groups)-1)<1e-6 for v in o.data.vertices)
    s.frame_set(1);limbs.hide_render=True;render(os.path.join(OUT,'previews',prefix+'_reference_form.png'));limbs.hide_render=False;render(os.path.join(OUT,'previews',prefix+'_rigged_rest.png'))
    if prefix=='Mustard':
        props=bpy.data.collections['OPTIONAL PROPS - cap and mustard dab (off by default)'];props.hide_render=False;props.hide_viewport=False
        limbs.hide_render=True;render(os.path.join(OUT,'previews',prefix+'_reference_with_props.png'));limbs.hide_render=False
        props.hide_render=True;props.hide_viewport=True
    s.frame_set(7);render(os.path.join(OUT,'previews',prefix+'_rigged_arms.png'));s.frame_set(13);render(os.path.join(OUT,'previews',prefix+'_rigged_legs.png'))
    s.frame_set(1);s.render.filepath='//../previews/'+prefix+'_rigged_rest.png';s.render.resolution_x=s.render.resolution_y=384;s.cycles.samples=32
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig;bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,'models',prefix+'_rigged.blend'),check_existing=False,compress=True,relative_remap=False)
    export(prefix)
    frames=os.path.join(AUD,prefix+'_frames');os.makedirs(frames,exist_ok=True)
    for f in range(1,25):s.frame_set(f);render(os.path.join(frames,'%03d.png'%f),256,4)
    s.frame_set(1)
    meshrows=[{'name':o.name,'vertices':len(o.data.vertices),'polygons':len(o.data.polygons),'weight_groups':[g.name for g in o.vertex_groups]} for o in bpy.data.objects if o.type=='MESH']
    texrows=[{'name':i.name,'filepath':i.filepath,'packed':bool(i.packed_file),'source':i.source,'sha256':hashlib.sha256(i.packed_file.data).hexdigest() if i.packed_file else None} for i in bpy.data.images if i.name!='Render Result']
    report={'character':prefix,'geometry_origin':'Generated solely by this script from mathematical profiles, curves, ellipses and rounded parametric meshes; no existing model read','texture_origin':'Generated solely by seeded math/noise pencil palette, no input image sampled','reference_use':'Manually inspected front silhouette and face proportions; reference JPG not embedded or distributed','model_license':'CC0-1.0; owner authorized commercial use, modification and redistribution for all generated model assets and code','mesh_data':meshrows,'textures':texrows,'rig_bones':[b.name for b in rig.data.bones],'action':{'name':a.name,'fps':12,'frames':[1,25],'seconds':2},'arms_displacements':arms,'legs_displacements':legs,'creation_seconds':round(time.monotonic()-started,2)}
    with open(os.path.join(AUD,prefix+'_creation.json'),'w',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
    print('CREATED',prefix,flush=True)

if __name__=='__main__':
    for prefix in ['Yuzu','Chili','Myoga']:
        if not args.only or args.only==prefix:build(prefix)
