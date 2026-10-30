import { useEffect, useState } from 'react'
import { FURNITURE, furnitureUrl, type FurnitureItem } from './owlLayout'
import { FURNITURE_EDIT_MODE_UPDATED, FURNITURE_FEEDBACK, FURNITURE_LAYOUT_UPDATED, FURNITURE_SELECTED, officeGameEvents } from './events'
import './officeWorkshop.css'

export function FurnitureEditor() {
  const [editing,setEditing]=useState(false)
  const [collapsed,setCollapsed]=useState(false)
  const [layout,setLayout]=useState<FurnitureItem[]>(()=>officeGameEvents.currentFurnitureLayout())
  const [selected,setSelected]=useState<string|null>(null)
  const [feedback,setFeedback]=useState('')
  useEffect(()=>{
    const update=(event:Event)=>setLayout((event as CustomEvent<FurnitureItem[]>).detail)
    const select=(event:Event)=>setSelected((event as CustomEvent<string|null>).detail)
    const feedback=(event:Event)=>setFeedback((event as CustomEvent<string>).detail)
    const mode=(event:Event)=>{setEditing((event as CustomEvent<boolean>).detail);setCollapsed(false)}
    officeGameEvents.addEventListener(FURNITURE_LAYOUT_UPDATED,update)
    officeGameEvents.addEventListener(FURNITURE_SELECTED,select)
    officeGameEvents.addEventListener(FURNITURE_FEEDBACK,feedback)
    officeGameEvents.addEventListener(FURNITURE_EDIT_MODE_UPDATED,mode)
    return ()=>{
      officeGameEvents.removeEventListener(FURNITURE_LAYOUT_UPDATED,update)
      officeGameEvents.removeEventListener(FURNITURE_SELECTED,select)
      officeGameEvents.removeEventListener(FURNITURE_FEEDBACK,feedback)
      officeGameEvents.removeEventListener(FURNITURE_EDIT_MODE_UPDATED,mode)
      officeGameEvents.setFurnitureEditMode(false)
    }
  },[])
  const item=layout.find(item=>item.id===selected)
  const toggle=()=>{const next=!editing;setEditing(next);setCollapsed(false);officeGameEvents.setFurnitureEditMode(next)}
  return <>
    <button className={`owl-editor-toggle ${editing?'active':''}`} type="button" onClick={toggle} aria-label={editing?'Selesai mengatur furnitur':'Atur furnitur'} title={editing?'Selesai mengatur furnitur':'Atur furnitur'} aria-pressed={editing}>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><path d="M6 13V6a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v7M4 11v6h16v-6M7 17v4M17 17v4M4 13h16" strokeLinecap="round" strokeLinejoin="round"/></svg>
    </button>
    {editing&&<div className={`owl-workshop ${collapsed?'is-collapsed':''}`} onPointerDown={event=>event.stopPropagation()}>
      <div className="owl-workshop-head">
        <div><strong>Studio furnitur</strong><small>{layout.length} objek · tersimpan di browser ini</small></div>
        <button type="button" onClick={()=>setCollapsed(!collapsed)} aria-label={collapsed?'Buka katalog furnitur':'Ciutkan katalog furnitur'} aria-expanded={!collapsed}>{collapsed?'⌃':'⌄'}</button>
        <button type="button" className="owl-workshop-done" onClick={toggle}>Selesai</button>
      </div>
      {!collapsed&&<div className="owl-workshop-catalog" aria-label="Katalog furnitur">
        {FURNITURE.map(spec=><button type="button" key={spec.frame} title={`Tambah ${spec.name}`} aria-label={`Tambah ${spec.name}`} onClick={()=>{officeGameEvents.addFurniture(spec.frame);setCollapsed(true)}}><img src={furnitureUrl(spec.frame)} alt=""/><span>{spec.name}</span><b aria-hidden="true">+</b></button>)}
      </div>}
      <div className="owl-workshop-footer">
        <p role="status">{feedback||'Pilih posisi di lantai. Jika perlu, furnitur digeser sedikit agar jalur owl tetap terbuka.'}</p>
        {item&&<button type="button" className="owl-remove" onClick={()=>officeGameEvents.deleteFurniture(item.id)}>Hapus {FURNITURE[item.frame].name.toLowerCase()}</button>}
      </div>
    </div>}
  </>
}
