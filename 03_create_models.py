"""Own procedural geometry, seeded pencil textures, FK rigs and clips.

Blender 4.3.2: blender --factory-startup --background --threads 2 --python create_source.py -- --out OUTPUT --audit AUDIT
Visual reference silhouettes were inspected manually. No reference JPG, existing model,
texture, atlas, font or motion file is read by this generator.
The owner explicitly authorizes CC0-1.0 for the entire independently generated model,
including mesh, materials, textures, rig, test animation and code. Commercial use,
modification and redistribution are permitted. Reference JPGs are not embedded.
"""
import bpy,bmesh,math,random,os,json,hashlib,array,argparse,sys,struct,time
from mathutils import Vector,Quaternion
from mathutils.bvhtree import BVHTree

argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
p=argparse.ArgumentParser();p.add_argument('--out',default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))));p.add_argument('--audit',default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'technical-audit'));p.add_argument('--only',choices=['Okra','Daikon','Sansho']);args=p.parse_args(argv)
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
    for packed in im.packed_files:packed.filepath=im.filepath
    for packed in im.packed_files:packed.filepath='//../textures/'+file
    return im

def material(name,image):
    m=bpy.data.materials.new(name);m.use_nodes=True;nt=m.node_tree;b=nt.nodes.get('Principled BSDF');b.inputs['Roughness'].default_value=.88;b.inputs['Metallic'].default_value=0
    tex=nt.nodes.new('ShaderNodeTexImage');tex.name='Own seeded pencil texture';tex.image=image;nt.links.new(tex.outputs['Color'],b.inputs['Base Color'])
    return m

def create_materials(prefix):
    palettes={'Okra':(.65,.82,.60),'Daikon':(.96,.97,.89),'Sansho':(.63,.82,.93)}
    mats={'body':material(prefix+' own pencil body',texture(prefix+'_pencil_body','solid',palettes[prefix],size=512,seed={'Okra':601,'Daikon':702,'Sansho':803}[prefix]))}
    colors={'cocoa':(.43,.285,.18),'white':(.98,.98,.92),'pink':(.93,.54,.59),'red':(.86,.30,.23),'leaf':(.67,.80,.49),'cut':(.79,.87,.67),'hand':palettes[prefix],'blue':(.37,.72,.88),'purple':(.67,.64,.82),'gray':(.76,.76,.71),'grate':(.49,.48,.45)}
    for n,col in colors.items():mats[n]=material(prefix+' own pencil '+n,texture(prefix+'_pencil_'+n,'solid',col,size=128,seed=700+sum(map(ord,prefix+n))))
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
    data=bpy.data.meshes.new(name+' math mesh');data.from_pydata(verts,[],faces);data.update();bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(data);bm.free();o=bpy.data.objects.new(name,data);(collection or bpy.context.scene.collection).objects.link(o);o.data.materials.append(mat)
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

def star_points(cx,cz,r=.35,inner=.265,n=5):
    # Five broad lobes separated by concave flats, observed in the end slice.
    pts=[]
    for j in range(n*2):
        t=math.pi/2+2*math.pi*j/(n*2);radius=r if j%2==0 else inner
        pts.append((cx+radius*math.cos(t),cz+radius*math.sin(t)))
    return catmull(pts,5,True)

def star_prism(name,cx,cz,lengthvec,depth,mat,rim,cut):
    outline=star_points(cx,cz);n=len(outline);vec=Vector(lengthvec)
    front=[Vector((x,-depth,z)) for x,z in outline];back=[v+vec for v in front]
    verts=[tuple(v) for v in front+back];faces=[tuple(reversed(range(n))),tuple(n+i for i in range(n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    o=mesh(name,verts,faces,mat,smooth_faces=False)
    bevel=o.modifiers.new('Own softened pentagonal ridges','BEVEL');bevel.width=.013;bevel.segments=2
    mesh(name+' pale visible cut face',[(x,-depth-.014,z) for x,z in outline],[tuple(range(n))],cut)
    tube(name+' front cut pencil rim',[(x,-depth-.021,z) for x,z in outline],.017,rim,True)
    tube(name+' rear cut pencil rim',[tuple(v+Vector((0,-.018,0))) for v in back],.015,rim,True)
    for j in range(0,n,10):
        a=front[j]+Vector((0,-.008,0));b=back[j]+Vector((0,-.010,0));tube(name+' longitudinal cocoa ridge '+str(j),[tuple(a),tuple(b)],.010,rim)
    return o

def okra(m):
    # The long star prism and separate floating cross section are both design features.
    body=star_prism('Okra long five-lobed pod',.72,.59,(-1.65,.46,.76),.15,m['body'],m['cocoa'],m['cut'])
    fy=-.189
    for suffix,x in [('L',.615),('R',.845)]:ellipse('Okra pod brown oval eye.'+suffix,x,.635,.039,.083,fy,m['cocoa'])
    tube('Okra pod quiet smile',[(x,fy-.004,z) for x,z in catmull([(.53,.448),(.70,.425),(.87,.46)],7)],.014,m['cocoa'])
    cap=star_prism('Okra separate thin five-lobed slice',.17,1.96,(-.14,.12,.06),.12,m['body'],m['cocoa'],m['cut'])
    for suffix,x in [('L',.072),('R',.277)]:ellipse('Okra slice tall empty eye.'+suffix,x,2.00,.049,.120,-.158,m['white'],m['cocoa'])
    filled_shape('Okra slice small neutral mouth',[(.074,1.813),(.264,1.813),(.253,1.752),(.09,1.752)],-.161,m['white'],m['cocoa'],.013)
    return body,{'arm_z':.515,'arm_pivots':[.54,.86],'arm_y':-.15,'leg_x':[.57,.85],'leg_z':.39,'leg_y':-.15}

def loft_body(name,rows,mat,rim):
    segments=48;verts=[]
    for z,rx,ry,cx in rows:
        for j in range(segments):
            t=2*math.pi*j/segments;verts.append((cx+rx*math.cos(t),ry*math.sin(t),z))
    faces=[]
    for i in range(len(rows)-1):
        for j in range(segments):faces.append((i*segments+j,i*segments+(j+1)%segments,(i+1)*segments+(j+1)%segments,(i+1)*segments+j))
    faces.extend([tuple(reversed(range(segments))),tuple((len(rows)-1)*segments+j for j in range(segments))]);o=mesh(name,verts,faces,mat,smooth_faces=True)
    left=[(cx-rx,-.015,z) for z,rx,ry,cx in rows];right=[(cx+rx,-.015,z) for z,rx,ry,cx in rows]
    tube(name+' left soft brown silhouette',left,.012,rim);tube(name+' right soft brown silhouette',right,.012,rim)
    return o

def rounded_tray(m):
    # One attached flat accessory; the original is a grated plate, not a second radish.
    contour=[(-.71,-.76,.095),(.54,-.88,.095),(.78,-.50,.095),(.70,.42,.095),(-.53,.53,.095),(-.77,.15,.095)]
    pts=catmull(contour,6,True);bottom=[(x,y,.045) for x,y,z in pts];verts=pts+bottom;n=len(pts)
    o=mesh('Daikon flat gray grated plate',verts,[tuple(range(n)),tuple(reversed([n+i for i in range(n)]))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],m['gray'])
    tube('Daikon gray plate cocoa rim',pts,.022,m['grate'],True)
    for row in range(5):
        y=-.68+.15*row;pts=[]
        for j in range(13):
            x=-.47+j*.074;pts.append((x,y+.026*math.sin(j*math.pi/2),.103))
        tube('Daikon independent grated plate zigzag '+str(row),pts,.010,m['grate'])
    return o

def daikon(m):
    rows=[(.30,.38,.24,0),(.32,.43,.26,0),(.40,.45,.28,0),(.65,.46,.29,0),(1.1,.47,.30,0),(1.5,.46,.29,0),(1.81,.43,.27,0),(1.99,.36,.24,0),(2.08,.30,.22,0)]
    body=loft_body('Daikon rounded white original root',rows,m['body'],m['cocoa'])
    # Small root shoulder and four short cut green leaf stubs.
    for index,a,b,r in [(1,(-.19,.065,2.02),(-.23,.065,2.29),.075),(2,(-.065,.09,2.06),(-.08,.09,2.34),.085),(3,(.067,.025,2.06),(.075,.025,2.35),.089),(4,(.19,.055,2.03),(.24,.055,2.29),.075)]:stem('Daikon short cut green stem '+str(index),a,b,r,m['leaf'],m['cocoa'])
    fy=-.309
    for suffix,x in [('L',-.155),('R',.155)]:
        ellipse('Daikon worried oval brown eye.'+suffix,x,.89,.079,.102,fy,m['cocoa'])
        ellipse('Daikon white eye light.'+suffix,x-.015,.928,.027,.031,fy-.008,m['white'])
    for suffix,pts in [('L',[(-.29,1.143),(-.20,1.18),(-.12,1.23)]),('R',[(.12,1.23),(.20,1.18),(.29,1.143)])]:tube('Daikon anxious eyebrow.'+suffix,[(x,fy,z) for x,z in catmull(pts,6)],.015,m['cocoa'])
    for suffix,x in [('L',-.29),('R',.29)]:ellipse('Daikon light blue cheek.'+suffix,x,.707,.055,.04,fy-.005,m['blue'])
    tube('Daikon small level uncertain mouth',[(-.078,fy-.009,.673),(.078,fy-.009,.675)],.012,m['cocoa'])
    rounded_tray(m)
    return body,{'arm_z':.61,'arm_pivots':[-.425,.425],'leg_x':[-.21,.21],'leg_z':.35}

def sansho(m):
    # Body profile keeps the salamander-like round head, thin long tail and no pointed snout.
    profile=[(-1.44,.46),(-1.22,.36),(-.94,.38),(-.65,.46),(-.33,.59),(-.10,.75),(.08,.72),(.30,.78),(.57,.87),(.82,.95),(.86,1.25),(.75,1.56),(.52,1.78),(.18,1.85),(-.12,1.75),(-.32,1.51),(-.44,1.08),(-.64,.79),(-.98,.62),(-1.26,.58)]
    body,pts=extrusion('Sansho pale blue round head and long slender tail',profile,.195,m['body'],'Sansho',.045)
    tube('Sansho soft cocoa body pencil contour',[(x,-.21,z) for x,z in pts],.013,m['cocoa'],True)
    # Purple fin ribbons sit just behind the blue tail, with mathematically drawn scallops.
    upper=[(-1.44,.47),(-1.53,.59),(-1.41,.64),(-1.43,.73),(-1.29,.70),(-1.22,.79),(-1.09,.72),(-.99,.76),(-.90,.69),(-.81,.70),(-.73,.62),(-.64,.64),(-.58,.58),(-.43,.63),(-.56,.52),(-.97,.52)]
    lower=[(-1.45,.47),(-1.54,.40),(-1.43,.33),(-1.34,.35),(-1.27,.24),(-1.13,.26),(-1.04,.19),(-.91,.22),(-.82,.20),(-.72,.29),(-.60,.29),(-.53,.39),(-.39,.39),(-.42,.50),(-.94,.53)]
    for suffix,profile in [('upper',upper),('lower',lower)]:
        obj,edge=extrusion('Sansho original purple scalloped '+suffix+' tail fin',profile,.032,m['purple'],'Sansho',.01)
        # Shift the fin rearward to avoid covering the blue thin tail line.
        obj.location.y=.195;tube('Sansho '+suffix+' fin scalloped pencil edge',[(x,.154,z) for x,z in edge],.011,m['cocoa'],True)
    fy=-.252
    ellipse('Sansho left empty white round eye',.325,1.275,.091,.097,fy,m['white'],m['cocoa'])
    ellipse('Sansho right empty white round eye',.711,1.434,.083,.094,fy,m['white'],m['cocoa'])
    tube('Sansho friendly broad quiet smile',[(x,fy-.006,z) for x,z in catmull([(.24,1.068),(.38,1.025),(.57,1.07),(.75,1.13),(.817,1.19)],8)],.017,m['cocoa'])
    return body,{'arm_z':1.0,'arm_pivots':[-.43,.815],'leg_x':[.14,.65],'leg_z':.79,'leg_zs':[.79,.96]}

def setup_camera(prefix):
    s=bpy.context.scene;coll=bpy.data.collections.new('PREVIEW lights and camera');s.collection.children.link(coll)
    config={'Okra':((-.1,0,1.20),(0,-8,3.0),3.25),'Daikon':((0,0,1.15),(0,-8,4.0),3.25),'Sansho':((-.30,0,1.03),(0,-8,2.6),3.05)}
    target,pos,scale=config[prefix];target=Vector(target);cd=bpy.data.cameras.new('Preview camera');o=bpy.data.objects.new('Preview camera',cd);coll.objects.link(o);o.location=pos;o.rotation_euler=(target-o.location).to_track_quat('-Z','Y').to_euler();cd.type='ORTHO';cd.ortho_scale=scale;s.camera=o
    for name,pos,power,size in [('Key',(-3,-4,5),500,4),('Fill',(3,-3,3),350,4),('Rim',(0,3,4),200,3)]:
        ld=bpy.data.lights.new(name,'AREA');ld.energy=power;ld.size=size;light=bpy.data.objects.new(name,ld);coll.objects.link(light);light.location=pos;light.rotation_euler=(target-light.location).to_track_quat('-Z','Y').to_euler()
    s.world=bpy.data.worlds.new('Own neutral preview world');s.world.use_nodes=True;s.world.node_tree.nodes.get('Background').inputs['Strength'].default_value=.35
    s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=8;s.cycles.use_denoising=False;s.render.threads_mode='FIXED';s.render.threads=2;s.render.film_transparent=True;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';s.view_settings.view_transform='Standard';s.view_settings.look='None'
def make_rig(prefix,m,config):
    original=[o for o in bpy.data.objects if o.type=='MESH'];arm=bpy.data.armatures.new(prefix+' own FK bones');rig=bpy.data.objects.new(prefix+'_Rig',arm);bpy.context.scene.collection.objects.link(rig)
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT')
    def bone(name,h,t,parent=None):
        b=arm.edit_bones.new(name);b.head=h;b.tail=t
        if parent:b.parent=arm.edit_bones[parent]
    bone('root',(0,0,-.10),(0,0,.08));bone('body',(0,0,.10),(0,0,1.7),'root')
    for i,suffix in enumerate(['L','R']):
        sign=-1 if i==0 else 1;x=config['arm_pivots'][i];z=config['arm_z'];y=config.get('arm_y',0);bone('arm.'+suffix,(x,y,z),(x+sign*.19,y,z-.03),'body')
        x=config['leg_x'][i];z=config.get('leg_zs',[config['leg_z']]*2)[i];y=config.get('leg_y',0);bone('leg.'+suffix,(x,y,z),(x,y,z-.19),'root')
    bpy.ops.object.mode_set(mode='OBJECT')
    coll=bpy.data.collections.new('ADDED ROUNDED LIMBS - toggle viewport and render');bpy.context.scene.collection.children.link(coll)
    limbs=[]
    for i,suffix in enumerate(['L','R']):
        sign=-1 if i==0 else 1;x=config['arm_pivots'][i];z=config['arm_z'];y=config.get('arm_y',0);o=sphere(prefix+' added arm.'+suffix,(x+sign*.13,y,z-.025),(.13,.075,.074),m['hand'],coll);limbs.append((o,'arm.'+suffix))
        x=config['leg_x'][i];z=config.get('leg_zs',[config['leg_z']]*2)[i];y=config.get('leg_y',0);o=sphere(prefix+' added leg.'+suffix,(x,y-.01,z-.115),(.072,.088,.120),m['hand'],coll);limbs.append((o,'leg.'+suffix))
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

def rest_attachment_mesh_check(body,prefix):
    bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get();bvh=BVHTree.FromObject(body,deps);inv=body.evaluated_get(deps).matrix_world.inverted();results=[]
    for o in bpy.data.objects:
        if o.type!='MESH' or not o.name.startswith(prefix+' added '):continue
        evaluated=o.evaluated_get(deps);data=evaluated.to_mesh();inside=0;depths=[]
        for vert in data.vertices:
            point=inv@(evaluated.matrix_world@vert.co);nearest=bvh.find_nearest(point)
            if nearest[0] is not None:
                signed=(point-nearest[0]).dot(nearest[1])
                if signed<-1e-5:inside+=1;depths.append(-signed)
        evaluated.to_mesh_clear();assert inside>0,(o.name,'evaluated REST gap')
        results.append({'mesh':o.name,'evaluated_surface_vertices_inside_body':inside,'max_local_penetration':max(depths),'method':'Fresh evaluated body BVH signed nearest-surface normals at REST'})
    assert len(results)==4;return results

def build(prefix):
    started=time.monotonic();bpy.ops.wm.read_factory_settings(use_empty=True);m=create_materials(prefix);body,cfg={'Okra':okra,'Daikon':daikon,'Sansho':sansho}[prefix](m);rig,limbs=make_rig(prefix,m,cfg);a=action(prefix,rig);setup_camera(prefix)
    s=bpy.context.scene;contacts=rest_attachment_mesh_check(body,prefix);rest=positions();s.frame_set(7);arms=changes(rest,positions());s.frame_set(13);legs=changes(rest,positions());assert arms[prefix+' added arm.L']>1e-4 and arms[prefix+' added arm.R']>1e-4;assert legs[prefix+' added leg.L']>1e-4 and legs[prefix+' added leg.R']>1e-4
    for o in bpy.data.objects:
        if o.type=='MESH':assert all(abs(sum(g.weight for g in v.groups)-1)<1e-6 for v in o.data.vertices)
    s.frame_set(1);limbs.hide_render=True;render(os.path.join(OUT,'previews',prefix+'_reference_form.png'));limbs.hide_render=False;render(os.path.join(OUT,'previews',prefix+'_rigged_rest.png'))
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
    report={'character':prefix,'geometry_origin':'Generated solely by this script from mathematical profiles, curves, ellipses, lofts and rounded parametric meshes; no existing model read','texture_origin':'Generated solely by seeded math/noise pencil palette; no input image sampled','reference_use':'Manually inspected silhouette and expression; reference JPG not embedded or distributed','license_authorization':'CC0-1.0 for full independently generated model assets and source code under explicit owner permission; commercial use, modification and redistribution permitted','mesh_data':meshrows,'textures':texrows,'rig_bones':[b.name for b in rig.data.bones],'action':{'name':a.name,'fps':12,'frames':[1,25],'seconds':2},'evaluated_rest_attachment':contacts,'arms_displacements':arms,'legs_displacements':legs,'creation_seconds':round(time.monotonic()-started,2)}
    with open(os.path.join(AUD,prefix+'_creation.json'),'w',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
    print('CREATED',prefix,flush=True)

if __name__=='__main__':
    for prefix in ['Okra','Daikon','Sansho']:
        if not args.only or args.only==prefix:build(prefix)
