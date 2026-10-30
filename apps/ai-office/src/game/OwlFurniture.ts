import Phaser from 'phaser'
import { DEFAULT_LAYOUT, FURNITURE, LAYOUT_KEY, furnitureRect, loadLayout, resolvePlacement, type Point } from './owlLayout'
import { FURNITURE_ADD_REQUESTED, FURNITURE_DELETE_REQUESTED, FURNITURE_EDIT_MODE_UPDATED, FURNITURE_LAYOUT_RESET, officeGameEvents } from './events'

export class OwlFurniture {
  items = loadLayout()
  editing = false
  private sprites = new Map<string, Phaser.GameObjects.Image>()
  private pending: number | null = null
  private ghost: Phaser.GameObjects.Image | null = null
  private lastDrag = 0
  private viewScale = { x: 1, y: 1 }
  private listeners: Array<[string, EventListener]> = []
  constructor(
    private scene: Phaser.Scene,
    private agentPositions: () => Point[],
    private changed: () => void,
    private editChanged: (value: boolean) => void,
  ) {
    this.render()
    this.listen(FURNITURE_EDIT_MODE_UPDATED, (event) => this.setEditing((event as CustomEvent<boolean>).detail))
    this.listen(FURNITURE_ADD_REQUESTED, (event) => this.beginPlacement((event as CustomEvent<number>).detail))
    this.listen(FURNITURE_DELETE_REQUESTED, (event) => this.remove((event as CustomEvent<string>).detail))
    this.listen(FURNITURE_LAYOUT_RESET, () => {
      if(!this.editing)return
      this.items=structuredClone(DEFAULT_LAYOUT);this.commit('Susunan awal dipulihkan.');this.editChanged(true)
    })
    scene.input.on('pointermove', this.moveGhost, this)
    scene.input.on('pointerup', this.placePending, this)
    scene.input.keyboard?.on('keydown-ESC', this.cancelPlacement, this)
    scene.events.once(Phaser.Scenes.Events.SHUTDOWN, () => {
      for(const [type,listener] of this.listeners)officeGameEvents.removeEventListener(type,listener)
      this.ghost?.destroy()
    })
    this.setEditing(officeGameEvents.currentFurnitureEditMode())
  }
  private listen(type: string, listener: EventListener) {
    this.listeners.push([type,listener]);officeGameEvents.addEventListener(type,listener)
  }
  setViewScale(x: number, y: number) {
    this.viewScale = { x, y }
    for (const item of this.items) {
      const spec = FURNITURE[item.frame]
      this.sprites.get(item.id)?.setDisplaySize(spec.width*x, spec.width*spec.ratio*y)
    }
    if (this.ghost && this.pending !== null) {
      const spec = FURNITURE[this.pending]
      this.ghost.setDisplaySize(spec.width*x, spec.width*spec.ratio*y)
    }
  }
  private render() {
    this.sprites.forEach(sprite=>sprite.destroy());this.sprites.clear()
    for(const item of this.items){
      const spec=FURNITURE[item.frame],rect=furnitureRect(item)
      const image=this.scene.add.image(item.x,item.y,`furniture-${item.frame}`)
        .setDisplaySize(spec.width*this.viewScale.x,spec.width*spec.ratio*this.viewScale.y).setDepth(rect.y+rect.height)
        .setInteractive({cursor:this.editing?'move':'pointer',pixelPerfect:true,alphaTolerance:40})
      this.scene.input.setDraggable(image,this.editing)
      image.on('pointerup', (_p:Phaser.Input.Pointer,_x:number,_y:number,event:Phaser.Types.Input.EventData)=>{
        event.stopPropagation()
        if(_p.event?.target!==this.scene.game.canvas||this.scene.time.now-this.lastDrag<180||this.pending!==null)return
        officeGameEvents.selectFurniture(item.id)
      })
      image.on('dragstart',()=>{ this.cancelPlacement();officeGameEvents.selectFurniture(item.id) })
      image.on('drag',(_p:Phaser.Input.Pointer,x:number,y:number)=>{
        image.setPosition(Math.round(x/8)*8,Math.round(y/8)*8).setDepth(y+rect.height/2)
        this.lastDrag=this.scene.time.now
      })
      image.on('dragend',()=>{
        this.lastDrag=this.scene.time.now
        const next={...item,x:image.x,y:image.y}
        const result=resolvePlacement(next,this.items,this.agentPositions())
        if(!result.item){image.setPosition(item.x,item.y).setDepth(rect.y+rect.height);officeGameEvents.furnitureFeedback(result.error||'Posisi tidak tersedia.');return}
        this.items=this.items.map(row=>row.id===item.id?result.item!:row)
        this.commit(result.adjusted?'Furnitur digeser ke lantai aman terdekat agar jalur owl terbuka.':'Posisi tersimpan. Jalur owl diperbarui.')
      })
      this.sprites.set(item.id,image)
    }
    officeGameEvents.updateFurnitureLayout(this.items)
  }
  private commit(message: string) {
    let saved=true
    try {localStorage.setItem(LAYOUT_KEY,JSON.stringify(this.items))} catch {saved=false}
    this.render();this.changed()
    officeGameEvents.furnitureFeedback(saved?message:'Susunan aktif, tetapi browser tidak mengizinkan penyimpanan.')
  }
  private setEditing(value: boolean) {
    this.editing=value;this.cancelPlacement()
    // Saat halaman Office ditinggalkan, sprite sudah dihancurkan sebelum editor ditutup.
    this.sprites.forEach(sprite=>{if(!sprite.input)return;this.scene.input.setDraggable(sprite,value);sprite.input.cursor=value?'move':'pointer'})
    this.editChanged(value)
    officeGameEvents.furnitureFeedback(value?'Pilih objek untuk ditambahkan, atau geser furnitur yang sudah ada.':'')
  }
  private beginPlacement(frame: number) {
    this.cancelPlacement()
    if(!this.editing||!FURNITURE[frame])return
    if(this.items.length>=80){officeGameEvents.furnitureFeedback('Batas 80 furnitur tercapai. Hapus beberapa objek terlebih dahulu.');return}
    const spec=FURNITURE[frame]
    this.pending=frame
    this.ghost=this.scene.add.image(0,0,`furniture-${frame}`).setDisplaySize(spec.width*this.viewScale.x,spec.width*spec.ratio*this.viewScale.y).setAlpha(.6).setDepth(4000).setVisible(false)
    officeGameEvents.furnitureFeedback(`Klik lantai kosong untuk menaruh ${spec.name.toLowerCase()}. Esc untuk batal.`)
  }
  private moveGhost(pointer: Phaser.Input.Pointer) {
    if(!this.ghost)return
    const point=this.scene.cameras.main.getWorldPoint(pointer.x,pointer.y)
    this.ghost.clearTint().setPosition(Math.round(point.x/8)*8,Math.round(point.y/8)*8).setVisible(true)
  }
  private placePending(pointer: Phaser.Input.Pointer) {
    if(pointer.event?.target!==this.scene.game.canvas||this.pending===null||!this.editing)return
    const point=this.scene.cameras.main.getWorldPoint(pointer.x,pointer.y)
    const item={id:crypto.randomUUID(),frame:this.pending,x:Math.round(point.x/8)*8,y:Math.round(point.y/8)*8}
    const result=resolvePlacement(item,this.items,this.agentPositions())
    if(!result.item){this.ghost?.setTint(0xff8a8a);officeGameEvents.furnitureFeedback(result.error||'Posisi tidak tersedia.');return}
    this.items=[...this.items,result.item];this.cancelPlacement();this.commit(result.adjusted?'Furnitur ditempatkan di lantai aman terdekat.':'Furnitur ditambahkan. Susunan tersimpan di browser ini.')
    officeGameEvents.selectFurniture(result.item.id)
  }
  private remove(id: string) {
    if(!this.editing)return
    this.items=this.items.filter(item=>item.id!==id);this.commit('Furnitur dihapus dari susunan kantor.')
    officeGameEvents.selectFurniture(null)
  }
  private cancelPlacement() {this.pending=null;this.ghost?.destroy();this.ghost=null}
}
