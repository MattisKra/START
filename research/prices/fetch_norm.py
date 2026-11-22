# Writes norm/*.csv from values read by hand from the cited sources (see raw/ for saved copies).
import csv
H="source,item,unit,price_gross_eur,region,date,url,note,tag".split(",")
def w(name, rows):
    with open(f"norm/{name}.csv","w",newline="",encoding="utf-8") as f:
        c=csv.writer(f); c.writerow(H); c.writerows(rows)
w("apple",[])  # selfservicerepair.eu returns 403; Apple price estimator did not load; no values invented
U="https://www.awm-muenchen.de/fileadmin/Dateien_pdfs/WSH_Preisliste.pdf"
C="https://www.awm-muenchen.de/abfall-entsorgen/services/containerdienst"
S="https://www.awm-muenchen.de/abfall-entsorgen/services/sperrmuellabholung"
B="https://www.awm-muenchen.de/fileadmin/Dateien_pdfs/presse/Presse_2026/PM_Bauschutt.pdf"
M="Muenchen"; d="2026"
a=lambda i,u,p,url,n,t,src="awm_muenchen",r=M,dt=d:[src,i,u,p,r,dt,url,n,t]
SRH="https://files.stadtreinigung.hamburg/SRH251008_Preisliste_Recyclinghoefe_2026.pdf"
w("waste",[
a("Gartenabfaelle WSH+ (max 3 m3)","EUR/1000 kg",81.12,U,"as published, list undated (retrieved 2026); WSH+ only","green_waste"),
a("Gartenabfaelle WSH+ unter 200 kg","pauschal",15.00,U,"as published","green_waste"),
a("Gartenabfaelle WSH (max 1 m3)","m3",0.00,U,"kostenlos","green_waste"),
a("Sperrmuell und Holz WSH+ (unbegrenzt)","EUR/1000 kg",177.06,U,"as published; combined line Sperrmuell und Holz, no Altholz A1-A4 split","timber"),
a("Sperrmuell und Holz WSH+ unter 200 kg","pauschal",26.00,U,"as published","timber"),
a("Sperrmuell und Holz WSH (bis 2 m3)","m3",0.00,U,"kostenlos","timber"),
a("Bauschutt WSH+ (max 1 m3) pro Eimer ca. 10 kg, bis max 10 Eimer","Eimer",2.46,U,"as published; AWM press release 2026-08-18 says household Bauschutt only at WSH+ and chargeable from mid-Sept 2026, new rates not in it","soil_rubble"),
a("Bauschutt WSH+ ab 100 kg (mehr als 10 Eimer) bis 200 kg","pauschal",36.87,U,"as published","soil_rubble"),
a("Bauschutt WSH+ ueber 200 kg","EUR/1000 kg",245.82,U,"as published, anteilig zum Tonnenpreis","soil_rubble"),
a("Sperrmuellabholung Anfahrtspauschale","pauschal",50.00,S,"as published","sperrmuell_pickup"),
a("Sperrmuellabholung pro angefangenem m3","m3",20.00,S,"as published","sperrmuell_pickup"),
a("Sperrmuellabholung Terminabholung (Wunschleistung) zusaetzlich","pauschal",55.00,S,"as published","sperrmuell_pickup"),
a("Container Gartenabfall Entsorgung","EUR/1000 kg",81.12,C,"keine MwSt laut Seite","green_waste_container"),
a("Container Gartenabfall Transportpauschale","Abfuhr",226.53,C,"as published","green_waste_container"),
a("Container Sperrmuell Entsorgung","EUR/1000 kg",177.06,C,"zzgl. MwSt laut Seite, plus Transport und Miete; gross not computed","sperrmuell_container"),
a("Containermiete Absetzmulde 10 m3","Tag",1.80,C,"as published","container_rent"),
a("Containermiete Abrollcontainer 25-30 m3","Tag",2.55,C,"as published","container_rent"),
a("Gartenabfall/Laub Gewerbe","m3",33.00,SRH,"net 27,73; gross as published; private households free in haushaltsueblicher Menge","green_waste","srh_hamburg","Hamburg","2026-01-01"),
a("Altholz Kat. I-III Gewerbe","m3",52.00,SRH,"net 43,70; private households free","timber","srh_hamburg","Hamburg","2026-01-01"),
a("Altholz Kat. IV Gewerbe","m3",52.00,SRH,"net 43,70; private households free","timber","srh_hamburg","Hamburg","2026-01-01"),
a("Bauschutt privat","angefangene 100 l (max 500 l)",18.00,SRH,"inkl. MwSt as published","soil_rubble","srh_hamburg","Hamburg","2026-01-01"),
a("Bauschutt Gewerbe","angefangene 100 l (max 500 l)",21.00,SRH,"net 17,65; gross as published","soil_rubble","srh_hamburg","Hamburg","2026-01-01"),
a("lose sperrige Abfaelle Gewerbe","m3",52.00,SRH,"net 43,70; gross as published","sperrmuell","srh_hamburg","Hamburg","2026-01-01"),
])
T="https://taifun-software.de/app/uploads/2025/10/Preisatlas_2024_TAIFUN-komprimiert.pdf"
CI1="https://www.clean-invoice.com/kostenindex"; CI2="https://www.clean-invoice.com/lexikon/anfahrtspauschale"
g=lambda x:round(x*1.19,2)
r=[]
def t(item,net,region,tag,pg):
    r.append(["taifun_preisatlas",item,"h",g(net),region,"2024",T,f"net {net:.2f} x1.19 (net×1.19); survey 27.11.-13.12.2023; {pg}",tag])
for lvl,(b,de) in {"Meister/Techniker":(68.00,65.14),"Geselle":(59.43,56.03)}.items():
    t(f"Handwerk Durchschnitt {lvl} Bayern",b,"Bayern","rate_all_trades","p.2 (all trades)")
    t(f"Handwerk Durchschnitt {lvl} Deutschland",de,"Deutschland","rate_all_trades","p.2 (all trades)")
for tag,name,gs,ms in [("rate_plumber","SHK",60.80,70.04),("rate_electrician","Elektrotechnik",58.31,68.78),("rate_carpenter","Tischler & Schreiner",60.63,65.68),("rate_painter","Maler, Gipser & Stuckateur",58.07,65.03)]:
    t(f"{name} Meister/Techniker",ms,"Deutschland",tag,"p.3 national by trade; no Bayern split by trade published")
    t(f"{name} Geselle",gs,"Deutschland",tag,"p.3 national by trade; no Bayern split by trade published")
def c(item,lo,hi,tag,url,note,reg="Deutschland",dt="2026-02",unit="h"):
    for k,v in (("min",lo),("max",hi)):
        r.append(["clean_invoice",f"{item} ({k})",unit,g(v),reg,dt,url,f"net {v} x1.19 (net×1.19); {note}",tag])
c("Tischler",50,75,"rate_carpenter",CI1,"Stand Feb 2026, netto zzgl. MwSt")
c("Heizung/Sanitaer",60,90,"rate_plumber",CI1,"Stand Feb 2026, netto zzgl. MwSt")
c("Maler",45,65,"rate_painter",CI1,"Stand Feb 2026, netto zzgl. MwSt")
c("Elektriker",60,85,"rate_electrician",CI1,"Stand Feb 2026, netto zzgl. MwSt")
c("Elektriker Grossstadt Muenchen/Stuttgart/Frankfurt",70,90,"rate_electrician",CI1,"table; FAQ says Muenchen 70-85","Grossstaedte")
for tag,nm,(n1,n2),(f1,f2) in [("rate_electrician","Elektriker",(25,45),(45,80)),("rate_plumber","Installateur/Sanitaer",(30,50),(50,90)),("rate_painter","Maler",(20,40),(40,70)),("rate_carpenter","Tischler/Schreiner",(30,50),(50,85))]:
    c(f"Anfahrtspauschale {nm} Nahbereich",n1,n2,tag,CI2,"net basis only inferred, page does not say","Deutschland","2026-01-28","Anfahrt")
    c(f"Anfahrtspauschale {nm} bis 25 km",f1,f2,tag,CI2,"net basis only inferred, page does not say","Deutschland","2026-01-28","Anfahrt")
w("rates",r)
