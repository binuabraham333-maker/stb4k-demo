import Foundation; import CoreGraphics; import CoreText; import ImageIO; import UniformTypeIdentifiers
// render.swift <fonts dir> <specs.jsonl>: one picture per line. Each line: {"out", "w", "h", "bg" (null = transparent,
// "#RRGGBB", or ["#top", "#bottom"]), "items": [text | img | rect]} — coordinates from the top left.
let args = CommandLine.arguments
for name in ["AtkinsonHyperlegible-Regular.ttf", "AtkinsonHyperlegible-Bold.ttf"] {
    CTFontManagerRegisterFontsForURL(URL(fileURLWithPath: args[1]).appendingPathComponent(name) as CFURL, .process, nil)
}
func color(_ hex: String) -> CGColor {
    var h = hex.hasPrefix("#") ? String(hex.dropFirst()) : hex
    if h.count == 6 { h += "FF" }
    let v = UInt64(h, radix: 16)!
    return CGColor(red: CGFloat((v >> 24) & 255) / 255, green: CGFloat((v >> 16) & 255) / 255, blue: CGFloat((v >> 8) & 255) / 255, alpha: CGFloat(v & 255) / 255)
}
var images: [String: CGImage] = [:]
func image(_ path: String) -> CGImage {
    if let cached = images[path] { return cached }
    let src = CGImageSourceCreateWithURL(URL(fileURLWithPath: path) as CFURL, nil)!
    let img = CGImageSourceCreateImageAtIndex(src, 0, nil)!; images[path] = img; return img
}
let text = try! String(contentsOfFile: args[2], encoding: .utf8)
for line in text.split(separator: "\n") where !line.isEmpty {
    let spec = try! JSONSerialization.jsonObject(with: Data(line.utf8)) as! [String: Any]
    let w = spec["w"] as! Int, h = spec["h"] as! Int
    let ctx = CGContext(data: nil, width: w, height: h, bitsPerComponent: 8, bytesPerRow: 0, space: CGColorSpaceCreateDeviceRGB(),
                        bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
    ctx.translateBy(x: 0, y: CGFloat(h)); ctx.scaleBy(x: 1, y: -1)   // top-left origin
    if let bg = spec["bg"] as? String { ctx.setFillColor(color(bg)); ctx.fill(CGRect(x: 0, y: 0, width: w, height: h)) }
    if let bg = spec["bg"] as? [String] {
        let g = CGGradient(colorsSpace: CGColorSpaceCreateDeviceRGB(), colors: bg.map(color) as CFArray, locations: nil)!
        ctx.drawLinearGradient(g, start: .zero, end: CGPoint(x: CGFloat(w) * 0.35, y: CGFloat(h)),
                               options: [.drawsBeforeStartLocation, .drawsAfterEndLocation])
    }
    for item in spec["items"] as? [[String: Any]] ?? [] {
        let x = CGFloat(item["x"] as? Double ?? 0), y = CGFloat(item["y"] as? Double ?? 0)
        switch item["t"] as! String {
        case "rect":
            let r = CGRect(x: x, y: y, width: CGFloat(item["w"] as! Double), height: CGFloat(item["h"] as! Double))
            let radius = CGFloat(item["r"] as? Double ?? 0)
            ctx.addPath(CGPath(roundedRect: r, cornerWidth: radius, cornerHeight: radius, transform: nil))
            if let fill = item["color"] as? String { ctx.setFillColor(color(fill)); ctx.fillPath() }
            if let stroke = item["stroke"] as? String {
                ctx.addPath(CGPath(roundedRect: r, cornerWidth: radius, cornerHeight: radius, transform: nil))
                ctx.setStrokeColor(color(stroke)); ctx.setLineWidth(CGFloat(item["lw"] as? Double ?? 4)); ctx.strokePath()
            }
        case "img":
            let img = image(item["path"] as! String)
            let iw = CGFloat(item["w"] as! Double), ih = iw * CGFloat(img.height) / CGFloat(img.width)
            ctx.saveGState(); ctx.translateBy(x: x, y: y + ih); ctx.scaleBy(x: 1, y: -1)
            ctx.draw(img, in: CGRect(x: 0, y: 0, width: iw, height: ih)); ctx.restoreGState()
        default:   // text (one line); x is the left, centre or right edge by "align"; y is the top of the line
            let size = CGFloat(item["size"] as! Double)
            let font = CTFontCreateWithName((item["bold"] as? Bool == true ? "AtkinsonHyperlegible-Bold" : "AtkinsonHyperlegible-Regular") as CFString, size, nil)
            let attr = NSAttributedString(string: item["s"] as! String, attributes: [
                kCTFontAttributeName as NSAttributedString.Key: font,
                kCTForegroundColorAttributeName as NSAttributedString.Key: color(item["color"] as? String ?? "#FFFFFF")])
            let ctLine = CTLineCreateWithAttributedString(attr)
            var ascent: CGFloat = 0, descent: CGFloat = 0
            let width = CGFloat(CTLineGetTypographicBounds(ctLine, &ascent, &descent, nil))
            let align = item["align"] as? String ?? "left"
            let left = align == "center" ? x - width / 2 : align == "right" ? x - width : x
            if let box = item["box"] as? String {
                let pad = CGFloat(item["pad"] as? Double ?? 16)
                let r = CGRect(x: left - pad, y: y - pad * 0.6, width: width + pad * 2, height: ascent + descent + pad * 1.2)
                ctx.addPath(CGPath(roundedRect: r, cornerWidth: pad * 0.8, cornerHeight: pad * 0.8, transform: nil))
                ctx.setFillColor(color(box)); ctx.fillPath()
            }
            ctx.saveGState(); ctx.translateBy(x: left, y: y + ascent); ctx.scaleBy(x: 1, y: -1)
            ctx.textPosition = .zero; CTLineDraw(ctLine, ctx); ctx.restoreGState()
        }
    }
    let out = spec["out"] as! String
    let type = out.hasSuffix(".jpg") ? UTType.jpeg.identifier : UTType.png.identifier
    let dst = CGImageDestinationCreateWithURL(URL(fileURLWithPath: out) as CFURL, type as CFString, 1, nil)!
    CGImageDestinationAddImage(dst, ctx.makeImage()!, out.hasSuffix(".jpg") ? [kCGImageDestinationLossyCompressionQuality: 0.85] as CFDictionary : nil)
    CGImageDestinationFinalize(dst)
}
