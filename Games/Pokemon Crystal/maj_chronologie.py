"""Remplit la colonne Chronologie du tableau à partir du journal de Script Viewer.
Les répliques gardent leur numéro si elles en ont déjà un ; les nouvelles prennent la suite,
dans l'ordre de leur première apparition dans le journal.
Usage : python3 maj_chronologie.py "Pokemon Crystal.xlsx" "mGBA/journal.tsv" """
import csv, sys, openpyxl

def main(xlsx, journal):
    wb = openpyxl.load_workbook(xlsx)
    ws = wb.active
    hdr = [str(c.value or '').strip().lower() for c in ws[1]]
    cu, cc = hdr.index('uid') + 1, hdr.index('chronologie') + 1
    where, top = {}, 0
    for r in range(2, ws.max_row + 1):
        where[str(ws.cell(r, cu).value)] = r
        v = ws.cell(r, cc).value
        if isinstance(v, (int, float)): top = max(top, int(v))
    new = 0
    with open(journal, encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            if row['Type'] != 'R' or row['UID'] not in where: continue
            cell = ws.cell(where[row['UID']], cc)
            if cell.value is None:
                top += 1; new += 1; cell.value = top
    wb.save(xlsx)
    print(new, 'nouvelles répliques numérotées, dernier numéro :', top)

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
