"""Apply the third-pass labels and write the final label file.

unclear_reclassified_v2.json is unclear_reclassified.json (from
reclassify.py) with the publication-pass labels in pub_out/ applied. That pass
read the linked PubMed abstracts of trials that had no reason after the second
pass. Its label replaces theirs where it names a reason; where the abstract
names none, the label of reclassify.py stands (a rule may have given one
since). Run after reclassify.py.
"""

from paper_numbers import Numbers
from repo_files import LABELS, read_json, read_labels, write_json

v1 = read_json(LABELS + 'unclear_reclassified.json')
pub = read_labels('pub_out')

v2 = {
    n: pub[n] if pub.get(n, 'unclear') != 'unclear' else lab
    for n, lab in v1.items()
}
write_json(v2, LABELS + 'unclear_reclassified_v2.json')

read = sum(1 for n in v1 if n in pub)
named = sum(1 for n in v1 if pub.get(n, 'unclear') != 'unclear')
print(
    f'unclear_reclassified_v2.json: {len(v2)} labels; {read} read in the '
    f'publication pass, {named} given a reason'
)

nums = Numbers('merge_pub_labels')
nums.count('pass3.modelRead', read)
nums.count('pass3.byModel', named)
nums.save()
