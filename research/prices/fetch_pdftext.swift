import Foundation
import PDFKit
import Vision
import AppKit
// usage: swift fetch_pdftext.swift file.pdf  -> text layer, else Vision OCR of rendered pages
let doc = PDFDocument(url: URL(fileURLWithPath: CommandLine.arguments[1]))!
for i in 0..<doc.pageCount {
  let p = doc.page(at: i)!
  print("=== page \(i+1)")
  let t = p.string ?? ""
  if t.trimmingCharacters(in: .whitespacesAndNewlines).count > 40 { print(t); continue }
  let b = p.bounds(for: .mediaBox)
  let img = p.thumbnail(of: CGSize(width: b.width*3, height: b.height*3), for: .mediaBox)
  guard let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { continue }
  let req = VNRecognizeTextRequest()
  req.recognitionLanguages = ["de-DE"]; req.recognitionLevel = .accurate
  try? VNImageRequestHandler(cgImage: cg).perform([req])
  for o in req.results ?? [] { print(o.topCandidates(1)[0].string) }
}
