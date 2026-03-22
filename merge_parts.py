import glob,os
target=r'D:\Cloude_PR\projectsethergent-runtime\sharedesearch.md'
parts=sorted(glob.glob(r'D:\Cloude_PR\projectsethergent-runtime\sharedesearch_p*.md'))
with open(target,'w',encoding='utf-8') as out:
    for p in parts:
        out.write(open(p,'r',encoding='utf-8').read())
for p in parts: os.remove(p)
print('Merged',len(parts),'parts')
