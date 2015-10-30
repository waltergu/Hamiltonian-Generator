from BasicClass.AppPackPy import *
from BasicClass.QuadraticPy import *
from BasicClass.GeneratorPy import *
from BasicClass.NamePy import *
from scipy.linalg import eigh
import matplotlib.pyplot as plt 
class TBA(Engine):
    '''
    The TBA class provides a general algorithm to calculate physical quantities of non-interacting systems based on the tight-binding approximation. The BdG systems, i.e. phenomenological superconducting systems based on mean-field theory are also supported in a unified way. Apart from those inherited from its parent class Engine, TBA has the following attributes:
    1) name: the name of system;
    2) filling: the filling factor of the system;
    3) mu: the chemical potential of the system;
    4) generator: the operator generator;
    Supported apps and the corresponding run methods include:
    1) EB (energy bands) with method TBAEB,
    2) DOS (density of states) with TBADOS.
    '''
    
    def __init__(self,name=None,filling=0,mu=0,generator=None,**karg):
        self.name=Name(prefix=name,suffix=self.__class__.__name__)
        self.filling=filling
        self.mu=mu
        self.generator=generator
        if not self.generator is None:
            self.name.update(self.generator.parameters['const'])

    def matrix(self,k=[],**karg):
        self.generator.update(**karg)
        nmatrix=len(self.generator.table)
        result=zeros((nmatrix,nmatrix),dtype=GP.Q_dtype)
        for opt in self.generator.operators:
            phase=1 if len(k)==0 else exp(-1j*inner(k,opt.rcoords[0]))
            result[opt.seqs]+=opt.value*phase
            if self.generator.nambu:
                i,j=opt.seqs
                if i<nmatrix/2 and j<nmatrix/2: result[j+nmatrix/2,i+nmatrix/2]+=-opt.value*conjugate(phase)
        result+=conjugate(result.T)
        return result

    def all_eigvals(self,kspace=None):
        nmatrix=len(self.generator.table)
        result=zeros(nmatrix*(1 if kspace==None else kspace.rank))
        if kspace==None:
            result[...]=eigh(self.matrix(),eigvals_only=True)
        else:
            for i,k in enumerate(list(kspace.mesh)):
                result[i*nmatrix:(i+1)*nmatrix]=eigh(self.matrix(k=k),eigvals_only=True)
        return result

def TBAEB(engine,app):
    nmatrix=len(engine.generator.table)
    if app.path!=None:
        result=zeros((app.path.rank,nmatrix+1))
        if len(app.path.mesh.shape)==1:
            result[:,0]=app.path.mesh
        else:
            result[:,0]=array(xrange(app.path.rank))
        for i,parameter in enumerate(list(app.path.mesh)):
            result[i,1:]=eigh(engine.matrix(**{app.path.mode:parameter}),eigvals_only=True)
    else:
        result=zeros((2,nmatrix+1))
        result[:,0]=array(xrange(2))
        result[0,1:]=eigh(engine.matrix(),eigvals_only=True)
        result[1,1:]=result[0,1:]
    if app.save_data:
        savetxt(engine.dout+'/'+engine.name.full_name+'_EB.dat',result)
    if app.plot:
        plt.title(engine.name.full_name+'_EB')
        plt.plot(result[:,0],result[:,1:])
        if app.show:
            plt.show()
        else:
            plt.savefig(engine.dout+'/'+engine.name.full_name+'_EB.png')

def TBADOS(engine,app):
    result=zeros((app.ne,2))
    eigvals=engine.all_eigvals(app.BZ)
    for i,v in enumerate(linspace(eigvals.min(),eigvals.max(),num=app.ne)):
       result[i,0]=v
       result[i,1]=sum(app.delta/((v-eigvals)**2+app.delta**2))
    if app.save_data:
        savetxt(engine.dout+'/'+engine.name.full_name+'_DOS.dat',result)
    if app.plot:
        plt.title(engine.name.full_name+'_DOS')
        plt.plot(result[:,0],result[:,1])
        if app.show:
            plt.show()
        else:
            plt.savefig(engine.dout+'/'+engine.name.full_name+'_DOS.png')