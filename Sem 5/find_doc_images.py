import docx, os, re

doc = docx.Document('SIMGuard Capstone Report.docx')
rels = doc.part.rels
img_map = {}
for rel_id, rel in rels.items():
    if 'image' in rel.target_ref:
        img_map[rel_id] = os.path.basename(rel.target_ref)

for i, p in enumerate(doc.paragraphs):
    xml_str = p._p.xml
    if 'blip' in xml_str:
        embeds = re.findall(r'embed="(rId\d+)"', xml_str)
        next_text = doc.paragraphs[i+1].text.strip() if i+1 < len(doc.paragraphs) else ''
        prev_text = doc.paragraphs[i-1].text.strip() if i > 0 else ''
        curr_text = p.text.strip()
        for e in embeds:
            fname = img_map.get(e, e)
            print(f"Para {i:3d} | File: {fname:15s} | Curr: {curr_text[:40]} | Next: {next_text[:60]} | Prev: {prev_text[:40]}")

