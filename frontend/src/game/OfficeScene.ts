import Phaser from 'phaser'
import type { OfficeAgent } from '../types'
import { AGENTS_UPDATED, CAMERA_RESET_REQUESTED, CAMERA_ZOOM_REQUESTED, OFFICE_INPUT_BLOCKED, officeGameEvents } from './events'
import { OwlFurniture } from './OwlFurniture'
import { FURNITURE, INDEX_STATION, OfficeNavigator, ROOMS, WORLD, furnitureUrl, workPoint, type Point } from './owlLayout'
import { assetUrl } from './assetUrl'

export const OFFICE_WORLD_WIDTH = WORLD.width
export const OFFICE_WORLD_HEIGHT = WORLD.height
const MAP_KEY='owl-office-empty-v2'
const MAP_FRAME='owl-office-without-side-margins'
const MAP_SIDE_MARGIN=28
const OWL_SIZE=82
const MIN_ZOOM=1, MAX_ZOOM=2.2
const OWLS: Record<string,string>={coordinator:'nova',researcher:'pixel',tutor:'sora',planner:'tempo',analyst:'metric',keeper:'nexus',finance:'koin'}
const RELAX: Record<string,string>={coordinator:'Santai · merapikan headset',researcher:'Santai · membaca buku',tutor:'Santai · membaca cerita',planner:'Santai · meregangkan sayap',analyst:'Santai · istirahat sejenak',keeper:'Santai · mendengarkan musik',finance:'Santai · minum sebentar'}
type Bot={agent:OfficeAgent; signature:string; container:Phaser.GameObjects.Container; sprite:Phaser.GameObjects.Sprite; bubble:Phaser.GameObjects.Graphics; text:Phaser.GameObjects.Text; mood:Phaser.GameObjects.Text; token:number; timer?:Phaser.Time.TimerEvent; visual:'idle'|'walking'|'working'|'relaxing'|'error'; phase:number}
const busy=(agent:OfficeAgent)=>['running','queued','waiting'].includes(agent.state)

export class OfficeScene extends Phaser.Scene {
  private bots=new Map<string,Bot>()
  private furniture!:OwlFurniture
  private navigator!:OfficeNavigator
  private zoomTarget=MIN_ZOOM
  private panStart:{x:number;y:number;scrollX:number;scrollY:number}|null=null
  private suppressUntil=0
  private editing=false
  private readonly onAgents=(event:Event)=>this.syncAgents((event as CustomEvent<OfficeAgent[]>).detail)
  private readonly onZoom=(event:Event)=>this.adjustZoom((event as CustomEvent<number>).detail)
  private readonly onReset=()=>this.resetCamera()
  private readonly onInputBlock=(event:Event)=>{this.input.enabled=!(event as CustomEvent<boolean>).detail;this.panStart=null}

  constructor(){super('office-owls')}
  preload(){
    this.load.image(MAP_KEY,assetUrl('assets/office/edupad-office-empty-v2.png'))
    for(const name of Object.values(OWLS))this.load.spritesheet(`owl-${name}`,assetUrl(`assets/agents/owls/${name}-owl-sheet-v1.png`),{frameWidth:320,frameHeight:320,endFrame:15})
    for(const spec of FURNITURE)this.load.image(`furniture-${spec.frame}`,furnitureUrl(spec.frame))
  }
  create(){
    const camera=this.cameras.main
    camera.setBounds(0,0,WORLD.width,WORLD.height).centerOn(WORLD.width/2,WORLD.height/2)
    const mapTexture=this.textures.get(MAP_KEY)
    const mapSource=mapTexture.getSourceImage() as HTMLImageElement
    const mapScaleX=mapSource.width/WORLD.width
    if(!mapTexture.has(MAP_FRAME))mapTexture.add(
      MAP_FRAME,
      0,
      Math.round(MAP_SIDE_MARGIN*mapScaleX),
      0,
      Math.round((WORLD.width-MAP_SIDE_MARGIN*2)*mapScaleX),
      mapSource.height,
    )
    this.add.image(MAP_SIDE_MARGIN,0,MAP_KEY,MAP_FRAME)
      .setOrigin(0)
      .setDisplaySize(WORLD.width-MAP_SIDE_MARGIN*2,WORLD.height)
      .setDepth(-100)
    this.createAnimations();this.createRooms();this.createOccluders()
    this.furniture=new OwlFurniture(this,()=>Array.from(this.bots.values(),bot=>({x:bot.container.x,y:bot.container.y})),()=>{this.navigator=new OfficeNavigator(this.furniture.items)},enabled=>this.setEditing(enabled))
    this.navigator=new OfficeNavigator(this.furniture.items)
    this.input.on('pointerdown',this.onPointerDown,this)
    this.input.on('pointermove',this.onPointerMove,this)
    this.input.on('pointerup',()=>{this.panStart=null})
    this.input.on('gameout',()=>{this.panStart=null})
    this.input.on('wheel',(_pointer:Phaser.Input.Pointer,_objects:unknown[],_dx:number,dy:number)=>this.adjustZoom(dy>0?-.15:.15))
    officeGameEvents.addEventListener(AGENTS_UPDATED,this.onAgents)
    officeGameEvents.addEventListener(CAMERA_ZOOM_REQUESTED,this.onZoom)
    officeGameEvents.addEventListener(CAMERA_RESET_REQUESTED,this.onReset)
    officeGameEvents.addEventListener(OFFICE_INPUT_BLOCKED,this.onInputBlock)
    this.syncAgents(officeGameEvents.currentAgents());this.publishCamera()
    this.events.once(Phaser.Scenes.Events.SHUTDOWN,()=>{
      officeGameEvents.removeEventListener(AGENTS_UPDATED,this.onAgents)
      officeGameEvents.removeEventListener(CAMERA_ZOOM_REQUESTED,this.onZoom)
      officeGameEvents.removeEventListener(CAMERA_RESET_REQUESTED,this.onReset)
      officeGameEvents.removeEventListener(OFFICE_INPUT_BLOCKED,this.onInputBlock)
    })
  }
  private createAnimations(){
    for(const name of Object.values(OWLS))for(const [suffix,start,end,rate] of [['down',0,3,7],['side',4,7,7],['up',8,11,7],['work',12,15,4]] as const){
      const key=`owl-${name}-${suffix}`
      if(!this.anims.exists(key))this.anims.create({key,frames:this.anims.generateFrameNumbers(`owl-${name}`,{start,end}),frameRate:rate,repeat:-1})
    }
  }
  private createRooms(){
    for(const room of ROOMS){
      const label=this.add.text(room.x+room.width/2,room.y+12,room.label.toUpperCase(),{fontFamily:'Plus Jakarta Sans, Arial, sans-serif',fontSize:'14px',fontStyle:'bold',color:'#334652',backgroundColor:'#ffffffed',padding:{x:10,y:6}}).setOrigin(.5).setVisible(false).setDepth(5000)
      const zone=this.add.zone(room.x+room.width/2,room.y+room.height/2,room.width,room.height).setDepth(-50).setInteractive({cursor:'grab'})
      zone.on('pointerover',()=>{if(!this.editing)label.setVisible(true)})
      zone.on('pointerout',()=>label.setVisible(false))
      zone.on('pointerup',(pointer:Phaser.Input.Pointer)=>{if(pointer.event?.target===this.game.canvas&&!this.editing&&this.time.now>=this.suppressUntil)officeGameEvents.selectRoom(room.id)})
    }
  }
  private createOccluders(){
    // Exact source frames: cropped images retain their real pixel size (no squeezed strips).
    const texture=this.textures.get(MAP_KEY),source=texture.getSourceImage() as HTMLImageElement
    const sx=source.width/WORLD.width,sy=source.height/WORLD.height
    const strip=(a:number,b:number,y:number,h:number)=>{
      const x=Math.max(a,MAP_SIDE_MARGIN),right=Math.min(b,WORLD.width-MAP_SIDE_MARGIN)
      return {x,y,w:right-x,h}
    }
    const strips=[
      ...[[0,244],[316,684],[766,1126],[1204,1448]].map(([a,b])=>strip(a,b,392,66)),
      ...[[0,178],[250,522],[598,862],[942,1198],[1276,1448]].map(([a,b])=>strip(a,b,648,86)),
    ]
    strips.forEach((rect,i)=>{
      const key=`wall-occluder-${i}`
      if(!texture.has(key))texture.add(key,0,Math.round(rect.x*sx),Math.round(rect.y*sy),Math.round(rect.w*sx),Math.round(rect.h*sy))
      this.add.image(rect.x,rect.y,MAP_KEY,key).setOrigin(0).setDisplaySize(rect.w,rect.h).setDepth(rect.y+rect.h)
    })
  }
  private syncAgents(agents:OfficeAgent[]){
    for(const agent of agents){
      const bot=this.bots.get(agent.id)??this.createBot(agent)
      const terminal=['succeeded','failed','cancelled'].includes(agent.state)
      const signature=[agent.state,agent.room,agent.station_id??'',terminal?agent.updated_at:''].join('|')
      bot.agent=agent
      if(bot.signature===signature){if(busy(agent)&&bot.visual!=='walking')this.setBubble(bot,agent.task);continue}
      bot.signature=signature
      if(!this.editing)this.resume(bot)
    }
  }
  private createBot(agent:OfficeAgent){
    const start=workPoint(agent.id,this.furniture.items)
    const color=Phaser.Display.Color.HexStringToColor(agent.color).color
    const ring=this.add.ellipse(0,0,43,12,color,.14).setStrokeStyle(1,color,.5)
    const sprite=this.add.sprite(0,0,`owl-${OWLS[agent.id]??'nova'}`,0).setDisplaySize(OWL_SIZE,OWL_SIZE).setOrigin(.5,.86).setInteractive({cursor:'pointer',pixelPerfect:true,alphaTolerance:50})
    const bubble=this.add.graphics()
    const text=this.add.text(0,-88,'',{fontFamily:'Plus Jakarta Sans, Arial, sans-serif',fontSize:'13px',color:'#34454f',align:'center',wordWrap:{width:155}}).setOrigin(.5)
    const name=this.add.text(0,13,agent.name,{fontFamily:'Plus Jakarta Sans, Arial, sans-serif',fontSize:'12px',fontStyle:'bold',color:'#263a48',backgroundColor:'#ffffffdc',padding:{x:5,y:3}}).setOrigin(.5,0)
    const mood=this.add.text(24,-52,'',{fontFamily:'Arial, sans-serif',fontSize:'19px',fontStyle:'bold',color:'#678ca6'}).setVisible(false)
    const container=this.add.container(start.x,start.y,[ring,sprite,bubble,text,name,mood]).setDepth(start.y)
    const bot:Bot={agent,signature:'',container,sprite,bubble,text,mood,token:0,visual:'idle',phase:this.bots.size}
    sprite.on('pointerup',(_p:Phaser.Input.Pointer,_x:number,_y:number,event:Phaser.Types.Input.EventData)=>{
      event.stopPropagation()
      if(_p.event?.target!==this.game.canvas||this.editing||this.time.now<this.suppressUntil)return
      this.tweens.add({targets:sprite,angle:8,duration:85,yoyo:true,onComplete:()=>sprite.setAngle(0)})
      officeGameEvents.selectAgent(agent.id)
    })
    this.bots.set(agent.id,bot);return bot
  }
  private stop(bot:Bot){
    bot.token++;bot.timer?.remove(false)
    this.tweens.killTweensOf(bot.container);this.tweens.killTweensOf(bot.sprite);this.tweens.killTweensOf(bot.mood)
    bot.sprite.stop().setPosition(0,0).setAngle(0).clearTint().setAlpha(1)
    bot.mood.setVisible(false).setPosition(24,-52).setAlpha(1)
  }
  private resume(bot:Bot){
    this.stop(bot)
    if(bot.agent.state==='offline'){this.setBubble(bot,'Tidak terhubung');bot.sprite.setAlpha(.55);return}
    if(busy(bot.agent)){
      const destination=bot.agent.room==='knowledge-server'&&bot.agent.id!=='keeper'
        ? INDEX_STATION:workPoint(bot.agent.id,this.furniture.items)
      this.setBubble(bot,'Menuju tempat kerja')
      this.walk(bot,destination,()=>{
        bot.visual='working';this.play(bot,'work');this.setBubble(bot,bot.agent.task||'Sedang bekerja')
        if(bot.agent.state!=='running')this.play(bot,'work')
      });return
    }
    if(bot.agent.state==='failed'){
      bot.visual='error';bot.sprite.setFrame(12).setTint(0xffd6d6)
      bot.mood.setText('!').setColor('#d9475f').setVisible(true)
      this.setBubble(bot,'Ada kendala · perlu diperiksa')
      this.tweens.add({targets:bot.sprite,angle:{from:-5,to:5},duration:180,yoyo:true,repeat:7})
      bot.timer=this.time.delayedCall(3400,()=>{this.stop(bot);this.returnHome(bot)});return
    }
    if(bot.agent.state==='succeeded'||bot.agent.state==='cancelled'){
      this.setBubble(bot,bot.agent.state==='succeeded'?'Tugas selesai':'Tugas dibatalkan')
      bot.timer=this.time.delayedCall(1500,()=>this.returnHome(bot));return
    }
    this.returnHome(bot)
  }
  private returnHome(bot:Bot){
    if(this.editing||busy(bot.agent))return
    this.walk(bot,workPoint(bot.agent.id,this.furniture.items),()=>this.relax(bot))
  }
  private relax(bot:Bot){
    if(this.editing||busy(bot.agent))return
    this.stop(bot);bot.visual='relaxing';bot.phase++
    const reading=['researcher','tutor','finance'].includes(bot.agent.id)
    if(reading){this.play(bot,'work');this.setBubble(bot,RELAX[bot.agent.id])}
    else{
      bot.sprite.setFrame(0);bot.mood.setText(bot.phase%2?'z Z':'♪').setColor('#6089a0').setVisible(true)
      this.setBubble(bot,RELAX[bot.agent.id])
      this.tweens.add({targets:bot.sprite,y:-3,angle:{from:-2,to:2},duration:1100,yoyo:true,repeat:-1})
      this.tweens.add({targets:bot.mood,y:-66,alpha:.35,duration:1600,yoyo:true,repeat:-1})
    }
    bot.timer=this.time.delayedCall(4500+(bot.phase%5)*850,()=>this.patrol(bot))
  }
  private patrol(bot:Bot){
    if(this.editing||busy(bot.agent))return
    this.stop(bot);this.setBubble(bot,'Jeda · jalan santai')
    const points=[{x:160,y:510},{x:520,y:570},{x:850,y:494},{x:1150,y:570},{x:620,y:604}]
    const target=points.map((_,offset)=>points[(bot.phase+offset)%points.length])
      .find(point=>this.navigator.findPath({x:bot.container.x,y:bot.container.y},point))
    if(!target){this.returnHome(bot);return}
    this.walk(bot,target,()=>{
      this.setBubble(bot,'Istirahat sebentar');bot.sprite.setFrame(0);bot.visual='relaxing'
      bot.mood.setText('♪').setColor('#6089a0').setVisible(true)
      this.tweens.add({targets:bot.sprite,y:-3,duration:900,yoyo:true,repeat:2})
      bot.timer=this.time.delayedCall(2600,()=>{this.stop(bot);this.returnHome(bot)})
    })
  }
  private walk(bot:Bot,destination:Point,done:()=>void){
    const token=++bot.token
    const path=this.navigator.findPath({x:bot.container.x,y:bot.container.y},destination)
    if(!path){
      this.setBubble(bot,'Jalur terhalang · atur furnitur');bot.sprite.stop();bot.visual='idle'
      return
    }
    bot.visual='walking'
    const visit=(index:number)=>{
      if(token!==bot.token||this.editing)return
      const point=path[index]
      if(!point){bot.sprite.stop().setFlipX(false).setFrame(0);done();return}
      const dx=point.x-bot.container.x,dy=point.y-bot.container.y,distance=Math.hypot(dx,dy)
      if(distance<1){visit(index+1);return}
      if(Math.abs(dx)>Math.abs(dy)){bot.sprite.setFlipX(dx<0);this.play(bot,'side')}
      else{bot.sprite.setFlipX(false);this.play(bot,dy<0?'up':'down')}
      this.tweens.add({targets:bot.container,x:point.x,y:point.y,duration:distance*8,ease:'Linear',onUpdate:()=>bot.container.setDepth(bot.container.y),onComplete:()=>visit(index+1)})
    }
    visit(0)
  }
  private play(bot:Bot,action:string){bot.sprite.play(`owl-${OWLS[bot.agent.id]??'nova'}-${action}`,true)}
  private setBubble(bot:Bot,message:string){
    const text=message.length>55?`${message.slice(0,53)}…`:message
    bot.text.setText(text);bot.bubble.clear()
    if(!text)return
    const width=Math.min(185,Math.max(100,bot.text.width+24)),height=Math.max(32,bot.text.height+16),top=-88-height/2
    bot.bubble.fillStyle(0xffffff,.96).lineStyle(1,0xcbd5dd)
    bot.bubble.fillRoundedRect(-width/2,top,width,height,10).strokeRoundedRect(-width/2,top,width,height,10)
    bot.bubble.fillTriangle(-6,top+height,6,top+height,0,top+height+7)
  }
  private setEditing(enabled:boolean){
    this.editing=enabled
    for(const bot of this.bots.values()){
      this.stop(bot)
      if(enabled)this.setBubble(bot,'Jeda · menata kantor')
      else this.resume(bot)
    }
  }
  private onPointerDown(pointer:Phaser.Input.Pointer){
    if(pointer.event?.target!==this.game.canvas||this.editing||!pointer.leftButtonDown())return
    this.panStart={x:pointer.x,y:pointer.y,scrollX:this.cameras.main.scrollX,scrollY:this.cameras.main.scrollY}
  }
  private onPointerMove(pointer:Phaser.Input.Pointer){
    if(!this.panStart||!pointer.isDown||this.editing)return
    const dx=pointer.x-this.panStart.x,dy=pointer.y-this.panStart.y
    if(Math.hypot(dx,dy)>5)this.suppressUntil=this.time.now+180
    if(this.cameras.main.zoom<=MIN_ZOOM)return
    this.cameras.main.scrollX=this.panStart.scrollX-dx/this.cameras.main.zoom
    this.cameras.main.scrollY=this.panStart.scrollY-dy/this.cameras.main.zoom
  }
  private adjustZoom(delta:number){this.zoomTarget=Phaser.Math.Clamp(this.zoomTarget+delta,MIN_ZOOM,MAX_ZOOM);this.cameras.main.zoomTo(this.zoomTarget,220,'Sine.easeOut',true);this.publishCamera()}
  private resetCamera(){this.zoomTarget=MIN_ZOOM;this.cameras.main.zoomTo(MIN_ZOOM,220,'Sine.easeOut',true);this.cameras.main.pan(WORLD.width/2,WORLD.height/2,220,'Sine.easeOut',true);this.publishCamera()}
  private publishCamera(){officeGameEvents.updateCameraView({zoom:this.zoomTarget,canZoomIn:this.zoomTarget<MAX_ZOOM,canZoomOut:this.zoomTarget>MIN_ZOOM})}
}
