import number_puzzle
import json
print(number_puzzle.find_numbers(10, 50))
print(number_puzzle.find_frac_numbers(10, 50))

nonfrac_template = (
    "Reach exactly {target} using: {numone}, {numtwo}, {numthree}, {numfour}. "
    "Operations: + - x /. Each number used at most once. "
    "All intermediate results must be positive integers. "
    "FORBIDDEN INTERMEDIATE VALUE: {forbid}. "
    "Any calculation that produces {forbid} at any step is invalid. "
    "This puzzle has been verified to have at least one valid solution. "
    "Final line must be: Solution: [YOUR EQUATION]"
)

frac_template = (
    "Start with {numone}. "
    "Use exactly 3 operations to reach {target}. "
    "Allowed operations (used exactly once): Add {numtwo}, "
    "Multiply by {numthree}, Add {numfour}. "
    "FORBIDDEN INTERMEDIATE: Your result can NEVER equal {forbid} at any step. "
    "Try ALL possible orderings of the three operations. "
    "Final line must be: "
    "Solution: [OP1, OP2, OP3]"
)

outerdict = {}
i=0
for variant in number_puzzle.find_numbers(3000, 50):
    innerdict = {}
    innerdict["variant"] = variant
    numone = variant[0][0]
    numtwo = variant[0][1]
    numthree = variant[0][2]
    numfour = variant[0][3]
    forbid = variant[0][5]
    target = variant[0][4]
    innerdict["difficulty"] = variant[1]
    innerdict["prompt"] = nonfrac_template.format(
        numone = numone, numtwo = numtwo, numthree=numthree, numfour=numfour, target=target, forbid=forbid
    )
    outerdict[i] = innerdict
    i+= 1
    print(i)

print(outerdict)

with open("number_puzzles.jsonl", "w", encoding="utf-8") as f:
    for record in outerdict.values():
        json.dump(record, f)
        f.write("\n")
        
        
    
    
    
outerfrac = {}
for variant in number_puzzle.find_frac_numbers(3000, 50):
    innerdict = {}
    innerdict["variant"] = variant
    numone = variant[0][0]
    numtwo = variant[0][1]
    numthree = variant[0][2]
    numfour = variant[0][3]
    forbid = variant[0][4]
    target = variant[0][5]
    innerdict["difficulty"] = variant[1]
    innerdict["prompt"] = frac_template.format(
        numone = numone, numtwo = numtwo, numthree=numthree, numfour=numfour, target=target, forbid=forbid
    )
    outerfrac[i] = innerdict
    i+= 1
    

with open("frac_puzzles.jsonl", "w", encoding="utf-8") as f:
    for record in outerfrac.values():
        json.dump(record, f, default=str)
        f.write("\n")