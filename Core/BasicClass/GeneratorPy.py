'''
Generator.
'''
from ConstantPy import RZERO
from OperatorPy import *
from numpy.linalg import norm
from collections import OrderedDict
class Generator:
    '''
    This class provides methods to generate and update operators of a Hamiltonian according to the bonds of the model and the descriptions of its terms.
    Attributes:
        bonds: list of Bond
            The bonds of the model.
        table: Table
            The index-sequence table of the system
        parameters: dict
            It contains all model parameters, divided into two groups, the constant ones and the alterable ones.
        terms: dict
            It contains all terms contained in the model, divided into two groups, the constant ones and the alterable ones.
        nambu: logical
            A flag to tag whether the nambu space takes part.
        half: logical
            A flag to tag whether the generated operators contains its hermitian conjugate part.
        cache: dict
            The working space used to handle the generation and update of the operators.
    '''

    def __init__(self,bonds,table,terms=None,nambu=False,half=True):
        '''
        Constructor.
        Parameter:
            bonds: list of Bond
            table: Table
            terms: list of Term,optional
                All the terms that are contained in the model.
                Those terms having the attribute modulate will go into self.terms['alter'] and the others will go into self.terms['const'].
            nambu: logical,optional
            half: logical,optional
        '''
        self.bonds=bonds
        self.table=table
        self.parameters={}
        self.terms={}
        self.set_parameters_and_terms(terms)
        self.nambu=nambu
        self.half=half
        self.cache={}
        self.set_cache()

    def set_parameters_and_terms(self,terms):
        self.parameters['const']=OrderedDict()
        self.parameters['alter']=OrderedDict()
        self.terms['const']={}
        self.terms['alter']={}
        if not terms is None:
            for term in terms:
                if hasattr(term,'modulate'):
                    self.parameters['alter'][term.tag]=term.value
                    self.terms['alter'][term.tag]=+term
                else:
                    self.parameters['const'][term.tag]=term.value
                    lterm=+term
                    if lterm.__class__.__name__ in self.terms['const']:
                        self.terms['const'][lterm.__class__.__name__].extend(lterm)
                    else:
                        self.terms['const'][lterm.__class__.__name__]=lterm

    def set_cache(self):
        if 'const' in self.terms:
            self.cache['const']=OperatorList()
            for bond in self.bonds:
                for terms in self.terms['const'].itervalues():
                    self.cache['const'].extend(terms.operators(bond,self.table,half=self.half))
        if 'alter' in self.terms:
            self.cache['alter']={}
            for key in self.terms['alter'].iterkeys():
                self.cache['alter'][key]=OperatorList()
                for bond in self.bonds:
                    self.cache['alter'][key].extend(self.terms['alter'][key].operators(bond,self.table,half=self.half))

    def __str__(self):
        '''
        Convert an instance to string.
        '''
        result='Parameters:\n'
        if len(self.parameters['const']>0):
            result+='Constant part: '+str(self.parameters['const'])+'\n'
        if len(self.parameters['alter']>0):
            result+='Alterable part: '+str(self.parameters['alter'])+'\n'
        for key,obj in self.terms['const'].iteritems():
            result+=key+':\n'+str(obj)
        for key,obj in self.terms['alter'].iteritems():
            result+=key+':\n'+str(obj)
        return result

    @property
    def operators(self):
        '''
        This method returns all the operators generated by self.
        '''
        result=OperatorList()
        if 'const' in self.cache:
            result.extend(self.cache['const'])
        if 'alter' in self.cache:
            for opts in self.cache['alter'].itervalues():
                result.extend(opts)
        return result

    def update(self,**karg):
        '''
        This method updates the alterable operators by keyword arguments.
        '''
        if 'alter' in self.terms:
            masks={key:False for key in self.terms['alter'].iterkeys()}
            for key,term in self.terms['alter'].iteritems():
                nv=term[0].modulate(**karg)
                if nv is not None and norm(array(nv)-array(term[0].value))>RZERO:
                    term[0].value=nv
                    self.parameters['alter'][key]=nv
                    masks[key]=True
            for key,mask in masks.iteritems():
                if mask:
                    self.cache['alter'][key]=OperatorList()
                    for bond in self.bonds:
                        self.cache['alter'][key].extend(self.terms['alter'][key].operators(bond,self.table,half=self.half))
