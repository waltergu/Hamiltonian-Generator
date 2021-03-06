from Hamiltonian.Core.BasicClass.AppPackPy import *
from Hamiltonian.Core.BasicClass.QuadraticPy import *
from Hamiltonian.Core.BasicClass.HubbardPy import *
from Hamiltonian.Core.BasicClass.GeneratorPy import *
from Hamiltonian.Core.BasicClass.NamePy import *
from Hamiltonian.Core.BasicClass.BasisEPy import *
from Hamiltonian.Core.BasicClass.OperatorRepresentationPy import *
from Hamiltonian.Core.BasicAlgorithm.LanczosPy import *
from scipy.sparse.linalg import eigsh
from scipy.linalg import solve_banded,solveh_banded
from copy import deepcopy
import matplotlib.pyplot as plt
import os.path,sys
class ONR(Engine):
    '''
    The class ONR provides the methods to get the sparse matrix representation on the occupation number basis of an electron system. Apart from those inherited from its parent class Engine, it has the following attributes:
    1) ensemble: 'c' for canonical ensemble and 'g' for grand canonical ensemble;
    2) filling: the filling factor of the system;
    3) mu: the chemical potential of the system;
    4) basis: the occupation number basis of the system;
    5) nspin: a flag to tag whether the ground state of the system lives in the subspace where the spin up electrons equal the spin down electrons, 1 for yes and 2 for no; 
    6) lattice: the lattice of the system;
    7) terms: the terms of the system;
    8) nambu: a flag to tag whether pairing terms are involved;
    9) generators: a dict containing the needed operator generators, which generally has only one entry:
        (1) entry 'h' is the generator for the whole Hamiltonian;
    10) operators: a dict containing different groups of operators for diverse tasks, which generally has two entries:
        (1) entry 'h' includes "half" the operators of the Hamiltonian, and
        (2) entry 'sp' includes all the single-particle operators;
    11) matrix: the sparse matrix representation of the system;
    12) cache: the cache during the process of calculation.
    '''

    def __init__(self,ensemble='c',filling=0.5,mu=0,basis=None,nspin=1,lattice=None,terms=None,nambu=False,**karg):
        self.ensemble=ensemble
        self.filling=filling
        self.mu=mu
        if self.ensemble.lower()=='c':
            self.name.update(const={'filling':self.filling})
        elif self.ensemble.lower()=='g':
            self.name.update(alter={'mu':self.mu})
        self.basis=basis
        self.nspin=nspin if basis.basis_type=='ES' else 2
        self.lattice=lattice
        self.terms=terms
        self.nambu=nambu
        self.generators={}
        self.generators['h']=Generator(bonds=lattice.bonds,table=lattice.table(nambu=False),terms=terms,nambu=False,half=True)
        self.name.update(const=self.generators['h'].parameters['const'])
        self.name.update(alter=self.generators['h'].parameters['alter'])
        self.operators={}
        self.set_operators()
        self.cache={}

    def set_operators(self):
        '''
        Prepare the operators that will be needed in future calculations.
        Generally, there are two entries in the dict "self.operators":
        1) 'h': stands for 'Hamiltonian', which contains half of the operators of the Hamiltonian;
        2) 'sp': stands for 'single particle', which contains all the allowed or needed single particle operators. When self.nspin==1 and self.basis.basis_type=='es' (spin-conserved systems), only spin-down single particle operators are included.
        '''
        self.set_operators_hamiltonian()
        self.set_operators_single_particle()

    def set_operators_hamiltonian(self):
        self.operators['h']=self.generators['h'].operators

    def set_operators_single_particle(self):
        self.operators['sp']=OperatorList()
        table=self.lattice.table(nambu=self.nambu) if self.nspin==2 else subset(self.lattice.table(nambu=self.nambu),mask=lambda index: True if index.spin==0 else False)
        for index,sequence in table.iteritems():
            self.operators['sp'].append(E_Linear(1,indices=[index],rcoords=[self.lattice.points[index.scope+str(index.site)].rcoord],icoords=[self.lattice.points[index.scope+str(index.site)].icoord],seqs=[sequence]))
        self.operators['sp'].sort(key=lambda operator: operator.seqs[0])

    def update(self,**karg):
        '''
        Update the alterable operators.
        '''
        for generator in self.generators.itervalues():
            generator.update(**karg)
        self.name.update(alter=self.generators['h'].parameters['alter'])
        self.set_operators_hamiltonian()

    def set_matrix(self):
        '''
        Set the csc_matrix representation of the Hamiltonian.
        '''
        self.matrix=csr_matrix((self.basis.nbasis,self.basis.nbasis),dtype=complex128)
        for operator in self.operators['h']:
            self.matrix+=opt_rep(operator,self.basis,transpose=False)
        self.matrix+=conjugate(transpose(self.matrix))
        self.matrix=transpose(self.matrix)

    def gf(self,omega=None):
        '''
        Return the single particle Green's function of the system.
        '''
        if not 'GF' in self.apps:
            self.addapps(app=GF((len(self.operators['sp']),len(self.operators['sp'])),run=ONRGF))
        if not omega is None:
            self.apps['GF'].omega=omega
            self.runapps('GF')
        return self.apps['GF'].gf

    def gf_mesh(self,omegas):
        '''
        Return the mesh of the single particle Green's functions of the system.
        '''
        if 'gf_mesh' in self.cache:
            return self.cache['gf_mesh']
        else:
            result=zeros((omegas.shape[0],len(self.operators['sp']),len(self.operators['sp'])),dtype=complex128)
            for i,omega in enumerate(omegas):
                result[i,:,:]=self.gf(omega)
            self.cache['gf_mesh']=result
            return result

def ONRGFC(engine,app):
    nopt=len(engine.operators['sp'])
    if os.path.isfile(engine.din+'/'+engine.name.full+'_coeff.dat'):
        with open(engine.din+'/'+engine.name.full+'_coeff.dat','rb') as fin:
            app.gse=fromfile(fin,count=1)
            app.coeff=fromfile(fin,dtype=complex128)
        if len(app.coeff)==nopt*nopt*2*3*app.nstep:
            app.coeff=app.coeff.reshape((nopt,nopt,2,3,app.nstep))
            return
    app.coeff=zeros((nopt,nopt,2,3,app.nstep),dtype=complex128)
    engine.set_matrix()
    app.gse,gs=Lanczos(engine.matrix,vtype=app.vtype).eig(job='v')
    print 'gse:',app.gse
    if engine.basis.basis_type.lower() in ('es','ep'): engine.matrix=None
    for h in xrange(2):
        if h==0: print 'Electron part:'
        else: print 'Hole part:' 
        for j,optb in enumerate(engine.operators['sp']):
            for i,opta in enumerate(engine.operators['sp']):
                if engine.basis.basis_type.lower()=='es' and engine.nspin==2 and optb.indices[0].spin!=opta.indices[0].spin : continue
                mask=False
                if j==i and j==0 : mask=True
                if engine.basis.basis_type.lower()=='es' and engine.nspin==2 and j==i and j==nopt/2: mask=True
                if h==0:
                    if mask: onr=onr_eh(engine,optb.indices[0].dagger)
                    matj=opt_rep(optb.dagger,[engine.basis,onr.basis],transpose=True)
                    mati=opt_rep(opta.dagger,[engine.basis,onr.basis],transpose=True)
                else:
                    if mask: onr=onr_eh(engine,optb.indices[0])
                    matj=opt_rep(opta,[engine.basis,onr.basis],transpose=True)
                    mati=opt_rep(optb,[engine.basis,onr.basis],transpose=True)
                statei=mati.dot(gs)
                statej=matj.dot(gs)
                normj=norm(statej)
                statej[:]=statej[:]/normj
                lcz=Lanczos(onr.matrix,statej)
                for k in xrange(app.nstep):
                    if not lcz.cut:
                        app.coeff[i,j,h,0,k]=vdot(statei,statej)*normj
                        lcz.iter()
                app.coeff[i,j,h,1,0:len(lcz.a)]=array(lcz.a)
                app.coeff[i,j,h,2,0:len(lcz.b)]=array(lcz.b)
                print j*nopt+i,'...',
                sys.stdout.flush()
        print
    if app.save_data:
        with open(engine.din+'/'+engine.name.full+'_coeff.dat','wb') as fout:
            array(app.gse).tofile(fout)
            app.coeff.tofile(fout)

def onr_eh(self,index):
    if self.basis.basis_type.lower()=='eg':
        return self
    elif self.basis.basis_type.lower()=='ep':
        result=deepcopy(self)
        if index.nambu==CREATION:
            result.basis=BasisE((self.basis.nstate,self.basis.nparticle+1))
        else:
            result.basis=BasisE((self.basis.nstate,self.basis.nparticle-1))
        result.matrix=csr_matrix((result.basis.nbasis,result.basis.nbasis),dtype=complex128)
        result.set_matrix()
        return result
    else:
        result=deepcopy(self)
        if index.nambu==CREATION and index.spin==0:
            result.basis=BasisE(up=(self.basis.nstate[0],self.basis.nparticle[0]),down=(self.basis.nstate[1],self.basis.nparticle[1]+1))
        elif index.nambu==ANNIHILATION and index.spin==0:
            result.basis=BasisE(up=(self.basis.nstate[0],self.basis.nparticle[0]),down=(self.basis.nstate[1],self.basis.nparticle[1]-1))
        elif index.nambu==CREATION and index.spin==1:
            result.basis=BasisE(up=(self.basis.nstate[0],self.basis.nparticle[0]+1),down=(self.basis.nstate[1],self.basis.nparticle[1]))
        else:
            result.basis=BasisE(up=(self.basis.nstate[0],self.basis.nparticle[0]-1),down=(self.basis.nstate[1],self.basis.nparticle[1]))
        result.matrix=csr_matrix((result.basis.nbasis,result.basis.nbasis),dtype=complex128)
        result.set_matrix()
        return result

def ONRGF(engine,app):
    nmatrix=engine.apps['GFC'].nstep
    gse=engine.apps['GFC'].gse
    coeff=engine.apps['GFC'].coeff
    nopt=len(engine.operators['sp'])
    app.gf[...]=0.0
    buff=zeros((3,nmatrix),dtype=complex128)
    b=zeros(nmatrix,dtype=complex128)
    for i in xrange(nopt):
        for j in xrange(nopt):
            for h in xrange(2):
                b[...]=0;b[0]=1
                buff[0,1:]=coeff[i,j,h,2,0:nmatrix-1]*(-1)**(h+1)
                buff[1,:]=app.omega-(coeff[i,j,h,1,:]-gse)*(-1)**h
                buff[2,:]=coeff[i,j,h,2,:]*(-1)**(h+1)
                app.gf[i,j]+=inner(coeff[i,j,h,0,:],solve_banded((1,1),buff,b,overwrite_ab=True,overwrite_b=True,check_finite=False))

def ONRDOS(engine,app):
    engine.cache.pop('gf_mesh',None)
    erange=linspace(app.emin,app.emax,num=app.ne)
    result=zeros((app.ne,2))
    result[:,0]=erange
    result[:,1]=-2*imag(trace(engine.gf_mesh(erange[:]+engine.mu+1j*app.eta),axis1=1,axis2=2))
    if app.save_data:
        savetxt(engine.dout+'/'+engine.name.full+'_DOS.dat',result)
    if app.plot:
        plt.title(engine.name.full+'_DOS')
        plt.plot(result[:,0],result[:,1])
        if app.show:
            plt.show()
        else:
            plt.savefig(engine.dout+'/'+engine.name.full+'_DOS.png')
        plt.close()

def ONREB(engine,app):
    result=zeros((app.path.rank.values()[0],app.ns+1))
    if len(app.path.rank)==1 and len(app.path.mesh.values()[0].shape)==1:
        result[:,0]=app.path.mesh.values()[0]
    else:
        result[:,0]=array(xrange(app.path.rank.values()[0]))
    for i,paras in enumerate(app.path('+')):
        engine.update(**paras)
        engine.set_matrix()
        result[i,1:]=eigsh(engine.matrix,k=app.ns,which='SA',return_eigenvectors=False)
    if app.save_data:
        savetxt(engine.dout+'/'+engine.name.const+'_EB.dat',result)
    if app.plot:
        plt.title(engine.name.const+'_EB')
        plt.plot(result[:,0],result[:,1:])
        if app.show:
            plt.show()
        else:
            plt.savefig(engine.dout+'/'+engine.name.const+'_EB.png')
        plt.close()
