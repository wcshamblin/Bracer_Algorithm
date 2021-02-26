#!/usr/bin/python3
import copy
from collections import OrderedDict
from time import time
from json import dumps, load
from functools import reduce
from multiprocessing import Pool
from multiprocessing import cpu_count
from boxbreedutils import get_parents, combinate, breedercompat, jsonify, convertbreeder, findbreeder, findcompatbreeder

# Generate tree from distribution and target - this is poorly optimized
def treegen(distdict, target, breederlist):
    # simplebreeders follows the format of [iv, iv, iv] (sorted)
    tempbreeders = breederlist.copy()
    simplebreeders = []
    perfect = False
    treedict = {}
    sharedict = OrderedDict({iv:amount-1 for iv, amount in distdict.items()})
    treedict[len(distdict)] = [target]
    for level in list(range(1, len(distdict)))[::-1]:
        treedict[level] = []
        for child in treedict[level+1]:
            if not child: # Is an empty list placeholder - fill placeholders below
                treedict[level].append([])
                treedict[level].append([])
                continue # Restart loop

            # if type(child) != dict: # Isn't a breeder - we can split it!
            if not child["breeder"]: # Isn't a breeder - we can split it!
                child = convertbreeder(child) # dict -> list
                branched_parents, sharedict = get_parents(child, sharedict) # Split
                branched_parents = [convertbreeder(parent) for parent in branched_parents] # Convert split back into dict

                firstisbreeder, firstbreeder = findbreeder(branched_parents[0], tempbreeders)
                if firstisbreeder:
                    print("Found breeder")
                    tempbreeders.remove(firstbreeder)
                treedict[level].append(firstbreeder)

                if firstisbreeder: # They're both breeders, we need to do compat checking
                    addedcompat, secondbreeder = findcompatbreeder(branched_parents[1], firstbreeder, tempbreeders)
                    if addedcompat:
                        print("Found compat")
                        tempbreeders.remove(secondbreeder)
                    treedict[level].append(secondbreeder)

                else:
                    # Add without compat
                    secondisbreeder, secondbreeder = findbreeder(branched_parents[1], tempbreeders)
                    if secondisbreeder:
                        print("Found secondbreeder")
                        tempbreeders.remove(secondbreeder)
                    treedict[level].append(secondbreeder)

            else: # Is a breeder - don't split it, add placeholders to branch
                treedict[level].append([])
                treedict[level].append([])

        # Scoring
        score = 0
        if not tempbreeders: # No more breeders to take from - tree is perfect
            perfect = True
        else:
            for breeder in tempbreeders: 
                score += (2**len([sorted([iv for iv, state in breeder["ivs"].items() if state == True])])+1)
    return(treedict, perfect, score)



# Breed function
def boxbreed(data):
    # Data preprocessing
    breederlist = data["breeders"]

    # Set target
    target = data["target"]
    simpletarget = []
    for iv, state in data["target"]["ivs"].items():
        if state is not False:
            simpletarget.append(iv)
    

    distributions = {} # key:[list] of (sets)
    # Start with 1
    for lnum in range(2,7): # 2x - 6x
        distributions[lnum] = combinate(lnum)
    # Ditch obviously non-optimal distributions
    # In a 6x tree, if there is a 5x and 1 1xs, then you have to use the 5x in the most optimal tree


    # Generate all trees from distributions
    t1=time()
    procpool = Pool(cpu_count()) # Set up processing pool
    args = []
    treedict = {}
    for distribution in distributions[len(simpletarget)]:
        distdict={}
        for value, stat in zip(distribution, list(simpletarget)): # Low -> high
            distdict[stat] = value
        distdict=OrderedDict(reversed(list(distdict.items()))) # Reverse so we can iterate high -> low
        tree, perfect, score = treegen(distdict, target, breederlist)
        treedict[score] = tree
        if perfect:
            break
    treedict = treedict[min(treedict.keys())]    

    t2=time()
    # print("Treegen:", t2-t1)


    t1=time()
    # JSONify entire tree
    outtree = {}
    for lnum, breeders in treedict.items():
        outtree[lnum] = []
        for breeder in breeders:
            if type(breeder) == list:
                outtree[lnum].append(jsonify(breeder))
            else:
                outtree[lnum].append(breeder)
    t2=time()
    # print("JSONify:", t2-t1)

    return(outtree)


if __name__ == '__main__':
    with open("test.json") as data:
        data = load(data)
    print(dumps(boxbreed(data)))