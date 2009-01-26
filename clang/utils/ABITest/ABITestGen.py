#!/usr/bin/python

from pprint import pprint
import random, atexit, time
from random import randrange

from Enumeration import *
from TypeGen import *

####

class TypePrinter:
    def __init__(self, output, outputHeader=None, 
                 outputTests=None, outputDriver=None,
                 headerName=None, info=None):
        self.output = output
        self.outputHeader = outputHeader
        self.outputTests = outputTests
        self.outputDriver = outputDriver
        self.writeBody = outputHeader or outputTests or outputDriver
        self.types = {}
        self.testValues = {}
        self.testReturnValues = {}

        if info:
            for f in (self.output,self.outputHeader,self.outputTests,self.outputDriver):
                if f:
                    print >>f,info

        if self.writeBody:
            print >>self.output, '#include <stdio.h>\n'
            if self.outputTests:
                print >>self.outputTests, '#include <stdio.h>\n'

        if headerName:
            for f in (self.output,self.outputTests,self.outputDriver):
                if f is not None:
                    print >>f, '#include "%s"\n'%(headerName,)
        
        if self.outputDriver:
            print >>self.outputDriver, 'int main(int argc, char **argv) {'
            
    def finish(self):
        if self.outputDriver:
            print >>self.outputDriver, '  return 0;'
            print >>self.outputDriver, '}'

    def getTypeName(self, T):
        if isinstance(T,BuiltinType):
            return T.name
        name = self.types.get(T)
        if name is None:            
            name = 'T%d'%(len(self.types),)
            # Reserve slot
            self.types[T] = None
            if self.outputHeader:
                print >>self.outputHeader,T.getTypedefDef(name, self)
            else:
                print >>self.output,T.getTypedefDef(name, self)
                if self.outputTests:
                    print >>self.outputTests,T.getTypedefDef(name, self)
            self.types[T] = name
        return name
    
    def writeFunction(self, i, FT):
        args = ', '.join(['%s arg%d'%(self.getTypeName(t),i) for i,t in enumerate(FT.argTypes)])
        if not args:
            args = 'void'

        if FT.returnType is None:
            retvalName = None
            retvalTypeName = 'void'
        else:
            retvalTypeName = self.getTypeName(FT.returnType)
            if self.writeBody or self.outputTests:
                retvalName = self.getTestReturnValue(FT.returnType)

        fnName = 'fn%d'%(FT.index,)
        if self.outputHeader:
            print >>self.outputHeader,'%s %s(%s);'%(retvalTypeName, fnName, args)
        elif self.outputTests:
            print >>self.outputTests,'%s %s(%s);'%(retvalTypeName, fnName, args)
            
        print >>self.output,'%s %s(%s)'%(retvalTypeName, fnName, args),
        if self.writeBody:
            print >>self.output, '{'
            
            for i,t in enumerate(FT.argTypes):
                self.printValueOfType('    %s'%fnName, 'arg%d'%i, t)

            if retvalName is not None:
                print >>self.output, '  return %s;'%(retvalName,)
            print >>self.output, '}'
        else:
            print >>self.output, '{}'
        print >>self.output

        if self.outputDriver:
            print >>self.outputDriver, '  { extern void test_%s(void); test_%s(); }\n'%(fnName,fnName,)
            
        if self.outputTests:
            if self.outputHeader:
                print >>self.outputHeader, 'void test_%s(void);'%(fnName,)

            if retvalName is None:
                retvalTests = None
            else:
                retvalTests = self.getTestValuesArray(FT.returnType)
            tests = map(self.getTestValuesArray, FT.argTypes)
            print >>self.outputTests, 'void test_%s(void) {'%(fnName,)

            if retvalTests is not None:
                print >>self.outputTests, '  printf("%s: testing return.\\n");'%(fnName,)
                print >>self.outputTests, '  for (int i=0; i<%d; ++i) {'%(retvalTests[1],)
                args = ', '.join(['%s[%d]'%(t,randrange(l)) for t,l in tests])
                print >>self.outputTests, '    %s RV;'%(retvalTypeName,)
                print >>self.outputTests, '    %s = %s[i];'%(retvalName, retvalTests[0])
                print >>self.outputTests, '    RV = %s(%s);'%(fnName, args)
                self.printValueOfType('  %s_RV'%fnName, 'RV', FT.returnType, output=self.outputTests, indent=4)
                print >>self.outputTests, '  }'
            
            if tests:
                print >>self.outputTests, '  printf("%s: testing arguments.\\n");'%(fnName,)
            for i,(array,length) in enumerate(tests):
                for j in range(length):
                    args = ['%s[%d]'%(t,randrange(l)) for t,l in tests]
                    args[i] = '%s[%d]'%(array,j)
                    print >>self.outputTests, '  %s(%s);'%(fnName, ', '.join(args),)
            print >>self.outputTests, '}'

    def getTestReturnValue(self, type):
        typeName = self.getTypeName(type)        
        info = self.testReturnValues.get(typeName)
        if info is None:
            name = '%s_retval'%(typeName.replace(' ','_').replace('*','star'),)
            print >>self.output, '%s %s;'%(typeName,name)
            if self.outputHeader:
                print >>self.outputHeader, 'extern %s %s;'%(typeName,name)
            elif self.outputTests:                
                print >>self.outputTests, 'extern %s %s;'%(typeName,name)
            info = self.testReturnValues[typeName] = name
        return info

    def getTestValuesArray(self, type):
        typeName = self.getTypeName(type)        
        info = self.testValues.get(typeName)
        if info is None:
            name = '%s_values'%(typeName.replace(' ','_').replace('*','star'),)
            print >>self.outputTests, 'static %s %s[] = {'%(typeName,name)
            length = 0
            for item in self.getTestValues(type):
                print >>self.outputTests, '\t%s,'%(item,)
                length += 1
            print >>self.outputTests,'};'
            info = self.testValues[typeName] = (name,length)
        return info

    def getTestValues(self, t):
        if isinstance(t, BuiltinType):
            if t.name=='float':
                for i in ['0.0','-1.0','1.0']:
                    yield i+'f'
            elif t.name=='double':
                for i in ['0.0','-1.0','1.0']:
                    yield i
            elif t.name in ('void *'):
                yield '(void*) 0'
                yield '(void*) -1'
            else:
                yield '(%s) 0'%(t.name,)
                yield '(%s) -1'%(t.name,)
                yield '(%s) 1'%(t.name,)
        elif isinstance(t, RecordType):
            fieldValues = [list(self.getTestValues(f)) for f in t.fields]
            if not t.fields:
                yield '{ }'
            for i,values in enumerate(fieldValues):
                for v in values:
                    elements = map(random.choice,fieldValues)
                    elements[i] = v
                    yield '{ %s }'%(', '.join(elements))
        elif isinstance(t, ComplexType):
            for t in self.getTestValues(t.elementType):
                yield '%s + %s * 1i'%(t,t)
        elif isinstance(t, ArrayType):
            values = list(self.getTestValues(t.elementType))
            if not values:
                yield '{ }'
            for i in range(t.numElements):
                for v in values:
                    elements = [random.choice(values) for i in range(t.numElements)]
                    elements[i] = v
                    yield '{ %s }'%(', '.join(elements))
        else:
            raise NotImplementedError,'Cannot make tests values of type: "%s"'%(t,)

    def printValueOfType(self, prefix, name, t, output=None, indent=2):
        if output is None:
            output = self.output
        if isinstance(t, BuiltinType):
            if t.name.endswith('long long'):
                code = 'lld'
            elif t.name.endswith('long'):
                code = 'ld'
            elif t.name.split(' ')[-1] in ('_Bool','char','short','int'):
                code = 'd'
            elif t.name in ('float','double'):
                code = 'f'
            elif t.name == 'long double':
                code = 'Lf'
            else:
                code = 'p'
            print >>output, '%*sprintf("%s: %s = %%%s\\n", %s);'%(indent, '', prefix, name, code, name) 
        elif isinstance(t, RecordType):
            if not t.fields:
                print >>output, '%*sprintf("%s: %s (empty)\\n");'%(indent, '', prefix, name) 
            for i,f in enumerate(t.fields):
                fname = '%s.field%d'%(name,i)
                self.printValueOfType(prefix, fname, f, output=output, indent=indent)
        elif isinstance(t, ComplexType):
            self.printValueOfType(prefix, '(__real %s)'%name, t.elementType, output=output,indent=indent)
            self.printValueOfType(prefix, '(__imag %s)'%name, t.elementType, output=output,indent=indent)
        elif isinstance(t, ArrayType):
            for i in range(t.numElements):
                # Access in this fashion as a hackish way to portably
                # access vectors.
                self.printValueOfType(prefix, '((%s*) &%s)[%d]'%(t.elementType,name,i), t.elementType, output=output,indent=indent)                            
        else:
            raise NotImplementedError,'Cannot print value of type: "%s"'%(t,)

import sys

def main():
    from optparse import OptionParser, OptionGroup
    parser = OptionParser("%prog [options] {indices}")
    parser.add_option("", "--mode", dest="mode",
                      help="autogeneration mode (random or linear) [default %default]",
                      type='choice', choices=('random','linear'), default='linear')
    parser.add_option("", "--count", dest="count",
                      help="autogenerate COUNT functions according to MODE",
                      type=int, default=0)
    parser.add_option("", "--min", dest="minIndex", metavar="N",
                      help="start autogeneration with the Nth function type  [default %default]",
                      type=int, default=0)
    parser.add_option("", "--max", dest="maxIndex", metavar="N",
                      help="maximum index for random autogeneration  [default %default]",
                      type=int, default=10000000)
    parser.add_option("", "--seed", dest="seed",
                      help="random number generator seed [default %default]",
                      type=int, default=1)
    parser.add_option("", "--use-random-seed", dest="useRandomSeed",
                      help="use random value for initial random number generator seed",
                      action='store_true', default=False)
    parser.add_option("-o", "--output", dest="output", metavar="FILE",
                      help="write output to FILE  [default %default]",
                      type=str, default='-')
    parser.add_option("-O", "--output-header", dest="outputHeader", metavar="FILE",
                      help="write header file for output to FILE  [default %default]",
                      type=str, default=None)
    parser.add_option("-T", "--output-tests", dest="outputTests", metavar="FILE",
                      help="write function tests to FILE  [default %default]",
                      type=str, default=None)
    parser.add_option("-D", "--output-driver", dest="outputDriver", metavar="FILE",
                      help="write test driver to FILE  [default %default]",
                      type=str, default=None)

    group = OptionGroup(parser, "Type Enumeration Options")
    # Builtins - Ints
    group.add_option("", "--no-char", dest="useChar",
                     help="do not generate char types",
                     action="store_false", default=True)
    group.add_option("", "--no-short", dest="useShort",
                     help="do not generate short types",
                     action="store_false", default=True)
    group.add_option("", "--no-int", dest="useInt",
                     help="do not generate int types",
                     action="store_false", default=True)
    group.add_option("", "--no-long", dest="useLong",
                     help="do not generate long types",
                     action="store_false", default=True)
    group.add_option("", "--no-long-long", dest="useLongLong",
                     help="do not generate long long types",
                     action="store_false", default=True)
    group.add_option("", "--no-unsigned", dest="useUnsigned",
                     help="do not generate unsigned integer types",
                     action="store_false", default=True)

    # Other builtins
    group.add_option("", "--no-bool", dest="useBool",
                     help="do not generate bool types",
                     action="store_false", default=True)
    group.add_option("", "--no-float", dest="useFloat",
                     help="do not generate float types",
                     action="store_false", default=True)
    group.add_option("", "--no-double", dest="useDouble",
                     help="do not generate double types",
                     action="store_false", default=True)
    group.add_option("", "--no-long-double", dest="useLongDouble",
                     help="do not generate long double types",
                     action="store_false", default=True)
    group.add_option("", "--no-void-pointer", dest="useVoidPointer",
                     help="do not generate void* types",
                     action="store_false", default=True)

    # Derived types
    group.add_option("", "--no-array", dest="useArray",
                     help="do not generate record types",
                     action="store_false", default=True)
    group.add_option("", "--no-complex", dest="useComplex",
                     help="do not generate complex types",
                     action="store_false", default=True)
    group.add_option("", "--no-record", dest="useRecord",
                     help="do not generate record types",
                     action="store_false", default=True)
    group.add_option("", "--no-union", dest="recordUseUnion",
                     help="do not generate union types",
                     action="store_false", default=True)
    group.add_option("", "--no-vector", dest="useVector",
                     help="do not generate vector types",
                     action="store_false", default=True)

    # Tuning 
    group.add_option("", "--no-function-return", dest="functionUseReturn",
                     help="do not generate return types for functions",
                     action="store_false", default=True)
    group.add_option("", "--vector-sizes", dest="vectorSizes",
                     help="comma separated list of sizes for vectors [default %default]",
                     action="store", type=str, default='4,8', metavar="N")

    group.add_option("", "--max-args", dest="functionMaxArgs",
                     help="maximum number of arguments per function [default %default]",
                     action="store", type=int, default=4, metavar="N")
    group.add_option("", "--max-array", dest="arrayMaxSize",
                     help="maximum array size [default %default]",
                     action="store", type=int, default=4, metavar="N")
    group.add_option("", "--max-record", dest="recordMaxSize",
                     help="maximum number of fields per record [default %default]",
                     action="store", type=int, default=4, metavar="N")
    group.add_option("", "--max-record-depth", dest="recordMaxDepth",
                     help="maximum nested structure depth [default %default]",
                     action="store", type=int, default=None, metavar="N")
    parser.add_option_group(group)
    (opts, args) = parser.parse_args()

    if not opts.useRandomSeed:
        random.seed(opts.seed)

    # Contruct type generator
    builtins = []
    ints = []
    if opts.useChar: ints.append(('char',1))
    if opts.useShort: ints.append(('short',2))
    if opts.useInt: ints.append(('int',4))
    # FIXME: Wrong size.
    if opts.useLong: ints.append(('long',4))
    if opts.useLongLong: ints.append(('long long',8))
    if opts.useUnsigned: 
        ints = ([('unsigned %s'%i,s) for i,s in ints] + 
                [('signed %s'%i,s) for i,s in ints])
    builtins.extend(ints)

    if opts.useBool: builtins.append(('_Bool',1))
    if opts.useFloat: builtins.append(('float',4))
    if opts.useDouble: builtins.append(('double',8))
    if opts.useLongDouble: builtins.append(('long double',16))
    # FIXME: Wrong size.
    if opts.useVoidPointer:  builtins.append(('void*',4))

    btg = FixedTypeGenerator([BuiltinType(n,s) for n,s in builtins])
    sbtg = FixedTypeGenerator([BuiltinType('char',1),
                               BuiltinType('int',4),
                               BuiltinType('float',4)])

    atg = AnyTypeGenerator()
    artg = AnyTypeGenerator()
    def makeGenerator(atg, subgen, useRecord, useArray):
        atg.addGenerator(btg)
        if useRecord and opts.useRecord:
            assert subgen 
            atg.addGenerator(RecordTypeGenerator(subgen, opts.recordUseUnion, 
                                                 opts.recordMaxSize))
        if opts.useComplex:
            # FIXME: Allow overriding builtins here
            atg.addGenerator(ComplexTypeGenerator(sbtg))
        if useArray and opts.useArray:
            assert subgen 
            atg.addGenerator(ArrayTypeGenerator(subgen, opts.arrayMaxSize))
        if opts.useVector:
            atg.addGenerator(VectorTypeGenerator(sbtg, 
                                                 map(int, opts.vectorSizes.split(','))))


    if opts.recordMaxDepth is None: 
        # Fully recursive, just avoid top-level arrays.
        subTG = AnyTypeGenerator()
        atg = AnyTypeGenerator()
        makeGenerator(subTG, atg, True, True)
        makeGenerator(atg, subTG, True, False)
    else:
        # Make a chain of type generators, each builds smaller
        # structures.
        base = AnyTypeGenerator()
        makeGenerator(base, None, False, False)
        for i in range(opts.recordMaxDepth):
            n = AnyTypeGenerator()
            makeGenerator(n, base, True, True)
            base = n
        atg = AnyTypeGenerator()
        makeGenerator(atg, base, True, False)

    ftg = FunctionTypeGenerator(atg, opts.functionUseReturn, opts.functionMaxArgs)

    # Override max,min,count if finite
    if opts.maxIndex is None:
        if ftg.cardinality is aleph0:
            opts.maxIndex = 10000000
        else:
            opts.maxIndex = ftg.cardinality
    opts.maxIndex = min(opts.maxIndex, ftg.cardinality)
    opts.minIndex = max(0,min(opts.maxIndex-1, opts.minIndex))
    if not opts.mode=='random':
        opts.count = min(opts.count, opts.maxIndex-opts.minIndex)

    if opts.output=='-':
        output = sys.stdout
    else:
        output = open(opts.output,'w')
        atexit.register(lambda: output.close())
        
    outputHeader = None
    if opts.outputHeader:
        outputHeader = open(opts.outputHeader,'w')
        atexit.register(lambda: outputHeader.close())
        
    outputTests = None
    if opts.outputTests:
        outputTests = open(opts.outputTests,'w')
        atexit.register(lambda: outputTests.close())

    outputDriver = None
    if opts.outputDriver:
        outputDriver = open(opts.outputDriver,'w')
        atexit.register(lambda: outputDriver.close())

    info = ''
    info += '// %s\n'%(' '.join(sys.argv),)
    info += '// Generated: %s\n'%(time.strftime('%Y-%m-%d %H:%M'),)
    info += '// Cardinality of function generator: %s\n'%(ftg.cardinality,)
    info += '// Cardinality of type generator: %s\n'%(atg.cardinality,)
    
    P = TypePrinter(output, 
                    outputHeader=outputHeader,
                    outputTests=outputTests,
                    outputDriver=outputDriver,
                    headerName=opts.outputHeader,
                    info=info)

    def write(N):
        try:            
            FT = ftg.get(N)
        except RuntimeError,e:
            if e.args[0]=='maximum recursion depth exceeded':
                print >>sys.stderr,'WARNING: Skipped %d, recursion limit exceeded (bad arguments?)'%(N,)
                return
            raise
        P.writeFunction(N, FT)

    if args:
        [write(int(a)) for a in args]

    for i in range(opts.count):
        if opts.mode=='linear':
            index = opts.minIndex + i
        else:
            index = opts.minIndex + int((opts.maxIndex-opts.minIndex) * random.random())
        write(index)

    P.finish()

if __name__=='__main__':
    main()

