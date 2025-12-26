link ="https://youtu.be/YstwVnuqwqc?si=21d2sgbL5yEjLywm"
ans=""
for i in link.split('/'):
    ans += i.replace('.','')
    ans += ' '

ans = ans.lower()
print(ans)