import random
from itertools import permutations
import doctest
import copy
from fractions import Fraction


def do_op(num1, num2, operator):
    '''
    This function takes two numbers and a string,
    and returns the correct operation on them
    >>> do_op(3, 2, "add")
    5
    >>> do_op(5, 2, "divide")
    2.5
    >>> do_op(3, 1, "multiply")
    3
    >>> do_op (5, 2, "subtract")
    3
    '''
    if operator == "add":
        return num1 + num2
    elif operator == "subtract":
        return num1 - num2
    elif operator == "multiply":
        return num1 * num2
    elif operator == "divide":
        if num2 != 0:
            return num1 / num2
        else:
            return -1
    
    
memo = {}
def helper(numbers: list, ops: list, forbid: int):
    """
    Given a list of numbers and a list of operations, 
    returns a list of all possible numbers
    via utilizing each operator (as many times) and number
    at most once, without hitting any negative value
    or a forbidden value.
    """
    hashh = (tuple(sorted(numbers)), forbid)
    if hashh in memo:
        return memo[hashh]
    retlist = []
    retlist = copy.copy(numbers)
    if len(numbers) == 1:
        return numbers
    loopnumbers = copy.copy(numbers)
    for one in range(len(loopnumbers)):
        for two in range(len(loopnumbers)):
            if one == two:
                continue
            i = loopnumbers[one]
            j = loopnumbers[two]
            for op in ops:
                intnums = copy.copy(numbers)
                intnums = [intnums[k] for k in range(len(intnums)) if k != one and k != two]
                if do_op(i, j, op) == forbid or do_op(i, j, op) <= 0 or not (do_op(i, j, op).is_integer()) :
                    continue
                intnums.append(do_op(i, j, op))
                intops = copy.copy(ops)
                #intops.remove(op)
                retlist = list(set(retlist) | set(helper(intnums, intops, forbid)))
    #print(retlist)
    memo[hashh] = retlist
    return retlist
    
def test_possible(target: int, numberlist: list, forbid: int):
    """
    tests whether it is possible, with the numbers in the list
    and addition, multiplication, division, and subtraction,
    to get to the target with each element only allowed once
    >>> test_possible(156, [4, 6, 25, 100], 150)
    False
    >>> test_possible(100, [10, 10, 20, 20], 32)
    True
    """
    #Create empty list that will contain all possible values
   
   

    if target in helper(numberlist, ["add", "subtract", "divide", "multiply"], forbid):
        return True
    else:
        return False
                    
                        
def find_numbers(n, hard):
    """
    returns list of numbers
    where we can utilize first 4
    numbers and any of + - * /
    to not get the target number
    with hard being the percentage of the list
    possible with a different forbidden value"""
    retlist = []
    i = 0
    while len(retlist) < n:
        easy_hard = random.randrange(0, 100)
        if easy_hard < hard:
            easy = False
        else: 
            easy = True
        intlist = copy.deepcopy(retlist)
        i += 1
        print(i)
        while len(retlist) == len(intlist):
            
            numone = random.randrange(1, 100)
            numtwo = random.randrange(1, 100)
            numthree = random.randrange(1, 100)
            numfour = random.randrange(1, 100)
            target = random.randrange(1, 200)
            forbid = random.randrange(1, 100)
            while forbid == target:
                forbid = random.randrange(1, 100)
            if easy == False:
                if test_possible(target, [numone, numtwo, numthree, numfour], -1) == True:
                    if test_possible(target, [numone, numtwo, numthree, numfour], forbid) == False:
                        intlist.append([[numone, numtwo, numthree, numfour, target, forbid], "hard"])
            else:
                if test_possible(target, [numone, numtwo, numthree, numfour], forbid) == False:
                        intlist.append([[numone, numtwo, numthree, numfour, target, forbid], "easy"])
        retlist = copy.deepcopy(intlist)
    return retlist



def frac_problem(numone, numtwo, numthree, numfour, forbid, target):
    combos = permutations([[numtwo, "add"], [numthree, "multiply"], [numfour, "add"]])
    retlist = []
    for combo in combos:
        loopval = numone
        valid = True
        for i in range(len(combo)):
            if (do_op(loopval, combo[i][0], combo[i][1]) != forbid):
                loopval = do_op(loopval, combo[i][0], combo[i][1])
            else:
                valid = False
        if valid == True:
            retlist.append(Fraction(loopval))
    if Fraction(target) in retlist:
        return True
    else:
        return False
            
            
            
#print(frac_problem(1/6, 1/4, 2, 1/6, 1/3, 2/3))


def find_frac_numbers(n, hard):
    retlist = []

    while len(retlist) < n:
        easy_hard = random.randrange(0, 100)
        if easy_hard < hard:
            easy = False
        else: 
            easy = True
        intlist = copy.deepcopy(retlist)
        while len(retlist) == len(intlist):
            numone = Fraction(1, random.randrange(2, 10))
            numtwo = Fraction(1, random.randrange(2, 10))
            numthree = (random.randrange(2, 10))
            numfour = Fraction(1, random.randrange(2, 10))
            
            numfive = (random.randrange(3, 10))
            target = Fraction(random.randrange(1, numfive), numfive)
            forbid = Fraction(1, random.randrange(2, 10))
            while target == forbid:
                forbid = Fraction(1, random.randrange(2, 10))
            if easy == True:
                if frac_problem(numone, numtwo, numthree, numfour, forbid, target) == False:
                    retlist.append([[numone, numtwo, numthree, numfour, forbid, target], "easy"])
            else:
                if frac_problem(numone, numtwo, numthree, numfour, 133333333, target) == True:
                    if frac_problem(numone, numtwo, numthree, numfour, forbid, target) == False:
                        retlist.append([[numone, numtwo, numthree, numfour, forbid, target], "hard"])
    return retlist

#print(find_frac_numbers(10, 50))
            
#print(Fraction(0.1 + 0.2) == Fraction(0.3))