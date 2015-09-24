#!/usr/bin/env python

import collections
import re
import os.path
import sys
from xml.dom.minidom import parse

class TestInfo(object):

    def __init__(self, xmlnode):
        self.fixture = xmlnode.getAttribute("classname")
        self.name = xmlnode.getAttribute("name")
        self.value_param = xmlnode.getAttribute("value_param")
        self.type_param = xmlnode.getAttribute("type_param")

        custom_status = xmlnode.getAttribute("custom_status")
        failures = xmlnode.getElementsByTagName("failure")

        if len(custom_status) > 0:
            self.status = custom_status
        elif len(failures) > 0:
            self.status = "failed"
        else:
            self.status = xmlnode.getAttribute("status")

        if self.name.startswith("DISABLED_"):
            self.status = "disabled"
            self.fixture = self.fixture.replace("DISABLED_", "")
            self.name = self.name.replace("DISABLED_", "")
        self.metrix = {}
        self.trees = []
        self.isTreeHasIPP = None
        self.ippFuncs = []
        self.firstFunction = ''
        self.totalIPPWeight = ''
        self.parseLongMetric(xmlnode, "bytesIn");
        self.parseLongMetric(xmlnode, "bytesOut");
        self.parseIntMetric(xmlnode, "samples");
        self.parseIntMetric(xmlnode, "outliers");
        self.parseFloatMetric(xmlnode, "frequency", 1);
        self.parseLongMetric(xmlnode, "min");
        self.parseLongMetric(xmlnode, "median");
        self.parseLongMetric(xmlnode, "gmean");
        self.parseLongMetric(xmlnode, "mean");
        self.parseLongMetric(xmlnode, "stddev");
        self.parseFloatMetric(xmlnode, "gstddev");
        self.parseFloatMetric(xmlnode, "time");
        self.parseStrTree(xmlnode, "functions_hierarchy");
        self.parseTotalWeight(xmlnode, "total_ipp_weight");

    def parseTotalWeight(self, xmlnode, name, default = "-1"):
        if xmlnode.hasAttribute(name):
            self.totalIPPWeight = xmlnode.getAttribute(name)
        else:
            self.totalIPPWeight = default

    '''
    static void printShift(cv::instr::InstrNode *pNode, cv::instr::InstrNode* pRoot)
    {
        // Print empty line for a big tree nodes
        if(pNode->m_pParent)
        {
            int parendIdx = pNode->m_pParent->findChild(pNode);
            if(parendIdx > 0 && pNode->m_pParent->m_childs[parendIdx-1]->m_childs.size())
            {
                printShift(pNode->m_pParent->m_childs[parendIdx-1]->m_childs[0], pRoot);
                printf("\n");
            }
        }

        // Check if parents have more childs
        std::vector<cv::instr::InstrNode*> cache;
        cv::instr::InstrNode *pTmpNode = pNode;
        while(pTmpNode->m_pParent && pTmpNode->m_pParent != pRoot)
        {
            cache.push_back(pTmpNode->m_pParent);
            pTmpNode = pTmpNode->m_pParent;
        }
        for(int i = (int)cache.size()-1; i >= 0; i--)
        {
            if(cache[i]->m_pParent)
            {
                if(cache[i]->m_pParent->findChild(cache[i]) == cache[i]->m_pParent->m_childs.size()-1)
                    printf("    ");
                else
                    printf("|   ");
            }
        }
    }

    static double calcLocWeight(cv::instr::InstrNode *pNode)
    {
        if(pNode->m_pParent && pNode->m_pParent->m_pParent)
            return ((double)pNode->m_payload.m_ticksAcc*100/pNode->m_pParent->m_payload.m_ticksAcc);
        else
            return 100;
    }

    static double calcGlobWeight(cv::instr::InstrNode *pNode)
    {
        cv::instr::InstrNode* globNode = pNode;

        while(globNode->m_pParent && globNode->m_pParent->m_pParent)
            globNode = globNode->m_pParent;

        return ((double)pNode->m_payload.m_ticksAcc*100/(double)globNode->m_payload.m_ticksAcc);
    }

    static void printNodeRec(cv::instr::InstrNode *pNode, cv::instr::InstrNode *pRoot)
    {
        printf("%s", (pNode->m_payload.m_funName.substr(0, 40) + ((pNode->m_payload.m_funName.size()>40)?"...":"")).c_str());

        // Write instrumentation falgs
        if(pNode->m_payload.m_instrType != cv::instr::TYPE_GENERAL || pNode->m_payload.m_implType != cv::instr::IMPL_PLAIN)
        {
            printf("<");
            if(pNode->m_payload.m_instrType == cv::instr::TYPE_WRAPPER)
                printf("W");
            else if(pNode->m_payload.m_instrType == cv::instr::TYPE_FUN)
                printf("F");
            else if(pNode->m_payload.m_instrType == cv::instr::TYPE_FUN_PTR_SET)
                printf("FPS");
            else if(pNode->m_payload.m_instrType == cv::instr::TYPE_FUN_PTR_CALL)
                printf("FPC");
            else if(pNode->m_payload.m_instrType == cv::instr::TYPE_MARKER)
                printf("MARK");

            if(pNode->m_payload.m_instrType != cv::instr::TYPE_GENERAL && pNode->m_payload.m_implType != cv::instr::IMPL_PLAIN)
                printf("_");

            if(pNode->m_payload.m_implType == cv::instr::IMPL_IPP)
                printf("IPP");
            else if(pNode->m_payload.m_implType == cv::instr::IMPL_OPENCL)
                printf("OCL");

            printf(">");
        }

        if(pNode->m_pParent)
        {
            printf(" - C:%d", pNode->m_payload.m_counter);
            printf(" T:%.4fms", (double)pNode->m_payload.m_ticksAcc/cv::getTickFrequency()*1000);
            if(pNode->m_pParent->m_pParent)
                printf(" L:%.0f%% G:%.0f%%", calcLocWeight(pNode), calcGlobWeight(pNode));
        }
        printf("\n");

        //Group childs
        std::vector<cv::String> groups;
        {
            bool bFound = false;
            for(size_t i = 0; i < pNode->m_childs.size(); i++)
            {
                bFound = false;
                for(size_t j = 0; j < groups.size(); j++)
                {
                    if(groups[j] == pNode->m_childs[i]->m_payload.m_funName)
                    {
                        bFound = true;
                        break;
                    }
                }
                if(!bFound)
                    groups.push_back(pNode->m_childs[i]->m_payload.m_funName);
            }
        }

        for(size_t g = 0; g < groups.size(); g++)
        {
            for(size_t i = 0; i < pNode->m_childs.size(); i++)
            {
                if(pNode->m_childs[i]->m_payload.m_funName == groups[g])
                {
                    printShift(pNode->m_childs[i], pRoot);

                    if(pNode->m_childs.size()-1 == pNode->m_childs[i]->m_pParent->findChild(pNode->m_childs[i]))
                        printf("\\---");
                    else
                        printf("|---");
                    printNodeRec(pNode->m_childs[i], pRoot);
                }
            }
        }
    }
    '''

    def parseStrTree(self, xmlnode, name, default = None):
        ippFlag = None
        firstFunctionFlag = None
        if xmlnode.hasAttribute(name):
            strTree = xmlnode.getAttribute(name)
            nodes   = strTree.split("(")
            treesNumber  = 0
            parenthesis  = 0
            ippFuncEntry = 0
            space = "    "
            tree  = []
            for node in nodes:
                treesNumber += 1
                for a in node:
                    if a == ')':
                        parenthesis -= 1
                node = node.replace(')','')
                if node.find("#0") > -1:
                    if firstFunctionFlag == None:
                        tmp = node[2:]
                        indAddInf = tmp.find(" - ")
                        tmp = tmp[0:indAddInf]
                        self.firstFunction = tmp
                        firstFunctionFlag = True

                if node.find("#3") > -1:
                    ippFlag = True
                    nonUniqueFlag = False
                    tmp = node[2:]
                    if tmp.startswith("ipp"):
                        indAddInf = tmp.find(" - ")
                        tmp = tmp[0:indAddInf]
                        for d in self.ippFuncs:
                            if d == tmp:
                                nonUniqueFlag = True
                        if nonUniqueFlag == False:
                            self.ippFuncs.append(tmp+'; ')
                        nonUniqueFlag = False

                node = node.replace('#0','')
                node = node.replace('#2','[W_IPP] ')
                node = node.replace('#3','[F_IPP] ')
                node = node.replace('#4','[FPS_IPP] ')
                node = node.replace('#5','[FPC_IPP] ')
                tree.append(space * parenthesis + node)
                parenthesis += 1
            self.trees = tree
            self.isTreeHasIPP = ippFlag
        else:
            self.trees = default
            self.ippFuncs = default

    def parseLongMetric(self, xmlnode, name, default = 0):
        if xmlnode.hasAttribute(name):
            tmp = xmlnode.getAttribute(name)
            val = long(tmp)
            self.metrix[name] = val
        else:
            self.metrix[name] = default

    def parseIntMetric(self, xmlnode, name, default = 0):
        if xmlnode.hasAttribute(name):
            tmp = xmlnode.getAttribute(name)
            val = int(tmp)
            self.metrix[name] = val
        else:
            self.metrix[name] = default

    def parseFloatMetric(self, xmlnode, name, default = 0):
        if xmlnode.hasAttribute(name):
            tmp = xmlnode.getAttribute(name)
            val = float(tmp)
            self.metrix[name] = val
        else:
            self.metrix[name] = default

    def parseStringMetric(self, xmlnode, name, default = None):
        if xmlnode.hasAttribute(name):
            tmp = xmlnode.getAttribute(name)
            self.metrix[name] = tmp.strip()
        else:
            self.metrix[name] = default

    def get(self, name, units="ms"):
        if name == "classname":
            return self.fixture
        if name == "name":
            return self.name
        if name == "fullname":
            return self.__str__()
        if name == "value_param":
            return self.value_param
        if name == "type_param":
            return self.type_param
        if name == "status":
            return self.status
        if name == "functions_hierarchy":
            return self.trees
        if name == "total_ipp_weight":
            return self.totalIPPWeight
        val = self.metrix.get(name, None)
        if not val:
            return val
        if name == "time":
            return self.metrix.get("time")
        if name in ["gmean", "min", "mean", "median", "stddev"]:
            scale = 1.0
            frequency = self.metrix.get("frequency", 1.0) or 1.0
            if units == "ms":
                scale = 1000.0
            if units == "mks":
                scale = 1000000.0
            if units == "ns":
                scale = 1000000000.0
            if units == "ticks":
                frequency = long(1)
                scale = long(1)
            return val * scale / frequency
        return val


    def dump(self, units="ms"):
        print "%s ->\t\033[1;31m%s\033[0m = \t%.2f%s" % (str(self), self.status, self.get("gmean", units), units)


    def getName(self):
        pos = self.name.find("/")
        if pos > 0:
            return self.name[:pos]
        return self.name


    def getFixture(self):
        if self.fixture.endswith(self.getName()):
            fixture = self.fixture[:-len(self.getName())]
        else:
            fixture = self.fixture
        if fixture.endswith("_"):
            fixture = fixture[:-1]
        return fixture

    def showtotalIPPWeight(self):
        if self.totalIPPWeight.startswith("-1"):
            self.totalIPPWeight = ""
        else:
            self.totalIPPWeight.replace(".",",")
        return '::'.join(filter(None, [self.totalIPPWeight]))

    def showTime(self):
        return '::'.join(filter(None, [str(self.metrix.get("time"))]))

    def showIPPFuncs(self):
        strippfuncs = ""
        for f in self.ippFuncs:
            strippfuncs += f
        return '::'.join(filter(None, [strippfuncs]))

    def showTree(self):
        strtree = ""
        for n in self.trees:
            strtree += n
            strtree += "\n"
        return '::'.join(filter(None, [strtree]))

    def showFirstFunction(self):
        return '::'.join(filter(None, [self.firstFunction]))

    def showifTreeHasIPP(self):
        if self.isTreeHasIPP:
            strIsTreeHasIPP = "Yes"
        else:
            strIsTreeHasIPP = "No"
        if self.trees == "":
            strIsTreeHasIPP = ""
        return '::'.join(filter(None, [strIsTreeHasIPP]))

    def param(self):
        return '::'.join(filter(None, [self.type_param, self.value_param]))

    def shortName(self):
        name = self.getName()
        fixture = self.getFixture()
        return '::'.join(filter(None, [name, fixture]))

    def testName(self):
        return self.fixture + "." + self.name

    def __str__(self):
        name = self.getName()
        fixture = self.getFixture()
        strtree = "\n"
        strIsTreeHasIPP = ""
        for n in self.trees:
            strtree += n
            strtree += "\n"
        if self.isTreeHasIPP:
            strIsTreeHasIPP = "\nTree has IPP\n"
        else:
            strIsTreeHasIPP = "\nTree has no IPP\n"
        return '::'.join(filter(None, [name, fixture, self.type_param, self.value_param, strtree, strIsTreeHasIPP, self.totalIPPWeight]))


    def __cmp__(self, other):
        r = cmp(self.fixture, other.fixture);
        if r != 0:
            return r
        if self.type_param:
            if other.type_param:
                r = cmp(self.type_param, other.type_param);
                if r != 0:
                     return r
            else:
                return -1
        else:
            if other.type_param:
                return 1
        if self.value_param:
            if other.value_param:
                r = cmp(self.value_param, other.value_param);
                if r != 0:
                     return r
            else:
                return -1
        else:
            if other.value_param:
                return 1
        return 0

# This is a Sequence for compatibility with old scripts,
# which treat parseLogFile's return value as a list.
class TestRunInfo(collections.Sequence):
    def __init__(self, properties, tests):
        self.properties = properties
        self.tests = tests

    def __len__(self):
        return len(self.tests)

    def __getitem__(self, key):
        return self.tests[key]

def parseLogFile(filename):
    log = parse(filename)

    properties = {
        attr_name[3:]: attr_value
        for (attr_name, attr_value) in log.documentElement.attributes.items()
        if attr_name.startswith('cv_')
    }

    tests = map(TestInfo, log.getElementsByTagName("testcase"))

    return TestRunInfo(properties, tests)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print "Usage:\n", os.path.basename(sys.argv[0]), "<log_name>.xml"
        exit(0)

    for arg in sys.argv[1:]:
        print "Processing {}...".format(arg)

        run = parseLogFile(arg)

        print "Properties:"

        for (prop_name, prop_value) in run.properties.items():
          print "\t{} = {}".format(prop_name, prop_value)

        print "Tests:"

        for t in sorted(run.tests):
            t.dump()

        print
