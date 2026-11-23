import React, {useEffect, useId, useMemo, useRef, useState} from 'react';
import {createRoot} from 'react-dom/client';
import {
  Home, FileText, Users, BarChart3, Settings, LogOut, Search, Bell,
  Leaf, ChevronRight, CheckCircle2, AlertTriangle, CircleDollarSign,
  Building2, ShieldCheck, BrainCircuit, TrendingUp, Download, Link2,
  Play, UserRoundCheck, Gauge, LineChart, Menu, X, Clock3, ArrowRight, ArrowLeft,
  CircleCheckBig, CircleX, ClipboardCheck, Sparkles, Landmark, WalletCards,
  Save, RotateCcw, Blocks
} from 'lucide-react';
import './styles.css';
import './aero.css';
import {authConfigurationError} from './firebase.js';
import {LedgerView, BlockchainExplorer} from './ledger/LedgerView.jsx';
import {signIn, observeSession, logoutUser, resetPassword} from './authAPI.js';
import {authErrorMessage} from './authErrors.js';
import {getMyProfile, profileErrorMessage, roleLabel, listLoanApplications, getLoanApplication, loanErrorMessage, LOAN_STATUSES, RISK_TIERS, LTV_GROUPS,
  claimLoanApplication, releaseLoanApplication, requestAssessment, getLatestAssessment, actionErrorMessage} from './api.js';
import {canClaim, canRelease, canRunAssessment, isRunning, decisionTone, tallyVotes, agentLabel, providerLabel,
  affordabilityRows, collateralRows, riskRows, riskFactors, breachedLimits} from './assessment/assessment.js';




const navItems = [
  ['dashboard','Dashboard',Home],
  ['pipeline','Loan Pipeline',FileText],
  ['brokers','Brokers',Users],
  ['analytics','Analytics',BarChart3],
  ['documents','Documents',FileText],
];

const applicationRows = [
  {id:'AL-1042', borrower:'BrightPath Capital', property:'Cork', amount:'€420k', ltv:'65%', risk:'Low', status:'AI Deliberated'},
  {id:'AL-1041', borrower:'Greenfield Partners', property:'Dublin', amount:'€285k', ltv:'70%', risk:'Medium', status:'Under Review'},
  {id:'AL-1040', borrower:'Summit Property Group', property:'Galway', amount:'€610k', ltv:'78%', risk:'High', status:'Applied'},
  {id:'AL-1039', borrower:'Ridgeview Capital', property:'Limerick', amount:'€250k', ltv:'61%', risk:'Low', status:'Conditionally Approved'},
  {id:'AL-1038', borrower:'Lakeside Ventures', property:'Waterford', amount:'€300k', ltv:'75%', risk:'Medium', status:'Under Review'},
];

// ALG4-68: AL-Web is for brokers and bank officers; borrowers use AL Mobile.
const BORROWER_ROLE='retail_borrower';
const BORROWER_PORTAL_MESSAGE='This portal is for brokers and bank officers. Borrowers sign in on the AL Mobile app.';

function App(){
  const [session,setSession]=useState({user:null,loading:!authConfigurationError,error:''});
  const [profile,setProfile]=useState({data:null,loading:false,error:''});
  // Kept apart from session.error, which the session observer clears on sign-out.
  const [portalNotice,setPortalNotice]=useState('');
  const [loggingOut,setLoggingOut]=useState(false);
  const [logoutError,setLogoutError]=useState('');
  const [preferences,setPreferences]=useState(loadPreferences);
  useEffect(()=>{
    document.documentElement.dataset.density=preferences.density;
    document.documentElement.dataset.reduceMotion=String(preferences.reduceMotion);
  },[preferences.density,preferences.reduceMotion]);
  const [page,setPage] = useState('dashboard');
  const [mobileOpen,setMobileOpen] = useState(false);
  const [decision,setDecision] = useState('Approve');
  const [scenario,setScenario] = useState({economic:'Recession', rate:2, price:-20});
  // Kept here so "Back to pipeline" returns to the same tab, filters and page.
  const [pipelineQuery,setPipelineQuery] = useState(DEFAULT_PIPELINE_QUERY);
  const [loanId,setLoanId] = useState(null);

  useEffect(()=>{
    if(authConfigurationError) return;
    let version=0;
    const unsubscribe=observeSession(async user=>{
      const current=++version;
      setSession({user:null,loading:true,error:''});
      try {
        // Validate restoration before showing the workspace; never store the token ourselves.
        if(user) await user.getIdToken();
        if(current!==version) return;
        setSession({user,loading:false,error:''});
        setPage('dashboard');
        setMobileOpen(false);
        setPipelineQuery(DEFAULT_PIPELINE_QUERY);
        setLoanId(null);
      } catch(error) {
        if(current===version) setSession({user:null,loading:false,error:authErrorMessage(error)});
      }
    },error=>{
      version++;
      setSession({user:null,loading:false,error:authErrorMessage(error)});
    });
    return ()=>{version++;unsubscribe();};
  },[]);

  // The profile shown in the workspace comes from AL-Core (GET /api/v1/users/me), not from local data.
  useEffect(()=>{
    if(!session.user){setProfile({data:null,loading:false,error:''});return;}
    let cancelled=false;
    setProfile({data:null,loading:true,error:''});
    getMyProfile()
      .then(data=>{
        if(cancelled) return;
        setProfile({data,loading:false,error:''});
        if(data?.role===BORROWER_ROLE){
          setPortalNotice(BORROWER_PORTAL_MESSAGE);
          logoutUser().catch(error=>setLogoutError(authErrorMessage(error)));
        }
      })
      .catch(error=>{if(!cancelled) setProfile({data:null,loading:false,error:profileErrorMessage(error)});});
    return ()=>{cancelled=true;};
  },[session.user]);

  async function handleLogout(){
    if(loggingOut) return;
    setLoggingOut(true);setLogoutError('');
    try {await logoutUser();}
    catch(error){setLogoutError(authErrorMessage(error));}
    finally {setLoggingOut(false);}
  }

  if(session.loading) return <div className="auth-loading" role="status"><Leaf size={28}/><span>Restoring your session...</span></div>;
  if(!session.user) return <Login sessionError={session.error} portalNotice={portalNotice} onSignInStart={()=>setPortalNotice('')}/>;
  // Never show the workspace to a borrower while their sign-out is in progress.
  if(profile.data?.role===BORROWER_ROLE) return <div className="auth-loading" role="status"><Leaf size={28}/>{logoutError
    ?<><span>Could not sign out. {logoutError}</span><button className="secondary" onClick={handleLogout} disabled={loggingOut}>Try again</button></>
    :<span>Signing out...</span>}</div>;

  return <div className="app-shell">
    <Sidebar page={page} setPage={setPage} mobileOpen={mobileOpen} setMobileOpen={setMobileOpen} onLogout={handleLogout} loggingOut={loggingOut}/>
    <div className="main-shell">
      <Topbar setMobileOpen={setMobileOpen}
        name={profile.data?.full_name||session.user.displayName||session.user.email||'Signed-in user'}
        subtitle={profile.loading?'Loading profile...':profile.data?roleLabel(profile.data.role):'Signed in'}/>
      <main key={page} id="main-content" className="page-wrap">
        {logoutError&&<p className="auth-error" role="alert">Could not sign out. {logoutError}</p>}
        {profile.error&&<p className="auth-error" role="alert">{profile.error}</p>}
        {page==='dashboard' && <Dashboard setPage={setPage}/>} 
        {page==='pipeline' && <Pipeline role={profile.data?.role} query={pipelineQuery} setQuery={setPipelineQuery}
          onOpenApplication={id=>{setLoanId(id);setPage('loan');}}/>}
        {page==='loan' && <LoanFile applicationId={loanId} currentUid={session.user.uid} role={profile.data?.role}
          onBack={()=>setPage('pipeline')} onOpenAudit={()=>setPage('audit')}/>}
        {page==='audit' && <AuditPage applicationId={loanId} currentUid={session.user.uid}
          onOpenFile={()=>setPage('loan')} onOpenPipeline={()=>setPage('pipeline')}/>}
        {page==='stress' && <Stress scenario={scenario} setScenario={setScenario}/>} 
        {page==='decision' && <Decision decision={decision} setDecision={setDecision}/>} 
        {page==='ledger' && <BlockchainExplorer Hero={Hero}/>}
        {page==='brokers' && <Brokers/>}
        {page==='analytics' && <Analytics/>}
        {page==='documents' && <Documents/>}
        {page==='settings' && <SettingsPage preferences={preferences} onSave={setPreferences} profile={profile.data}/>}
      </main>
    </div>
  </div>
}

function Sidebar({page,setPage,mobileOpen,setMobileOpen,onLogout,loggingOut}){
  return <>
    <aside className={`sidebar ${mobileOpen?'open':''}`} aria-label="Primary navigation">
      <div className="brand"><Leaf size={25}/><span>Agentic Lender</span></div>
      <nav>
        {navItems.map(([id,label,Icon])=><button key={id} className={page===id?'active':''} onClick={()=>{setPage(id);setMobileOpen(false)}}><Icon size={19}/><span>{label}</span></button>)}
        <button className={page==='audit'?'active':''} onClick={()=>{setPage('audit');setMobileOpen(false)}}><BrainCircuit size={19}/>AI Audit</button>
        <button className={page==='stress'?'active':''} onClick={()=>{setPage('stress');setMobileOpen(false)}}><Gauge size={19}/>Stress Testing</button>
        <button className={page==='decision'?'active':''} onClick={()=>{setPage('decision');setMobileOpen(false)}}><Link2 size={19}/>Settlement</button>
        <button className={page==='ledger'?'active':''} onClick={()=>{setPage('ledger');setMobileOpen(false)}}><Blocks size={19}/>Blockchain</button>
        <button className={page==='settings'?'active':''} onClick={()=>{setPage('settings');setMobileOpen(false)}}><Settings size={19}/><span>Settings</span></button>
      </nav>
      <div className="sidebar-quote">“Clear lending.<br/>Stronger outcomes.”</div>
      <button className="logout" onClick={onLogout} disabled={loggingOut}><LogOut size={19}/>{loggingOut?'Signing out...':'Logout'}</button>
    </aside>
    {mobileOpen && <button className="backdrop" aria-label="Close menu" onClick={()=>setMobileOpen(false)}/>} 
  </>
}

function Topbar({setMobileOpen,name,subtitle}){
  return <header className="topbar">
    <button className="icon-btn mobile-only" aria-label="Open menu" onClick={()=>setMobileOpen(true)}><Menu/></button>
    <div className="search"><Search size={18}/><input aria-label="Search" placeholder="Search loans, brokers, or documents..."/></div>
    <div className="top-actions"><button className="icon-btn" aria-label="Notifications"><Bell/></button><div className="avatar" aria-hidden="true">{name.split(/\s+/).filter(Boolean).map(part=>part[0]).slice(0,2).join('')}</div><div className="user-meta"><strong>{name}</strong><span>{subtitle}</span></div></div>
  </header>
}

function Login({sessionError,portalNotice,onSignInStart}){
  const [email,setEmail]=useState('');
  const [password,setPassword]=useState('');
  const [pending,setPending]=useState('');
  const [error,setError]=useState('');
  const [notice,setNotice]=useState('');
  async function handleSubmit(event){
    event.preventDefault();
    if(pending||authConfigurationError) return;
    setPending('signin');setError('');setNotice('');onSignInStart();
    try {await signIn(email,password);}
    catch(error){setError(authErrorMessage(error));}
    finally {setPassword('');setPending('');}
  }
  async function handleReset(event){
    const input=event.currentTarget.form.elements.email;
    if(!input.reportValidity()||pending||authConfigurationError) return;
    setPending('reset');setError('');setNotice('');
    try {await resetPassword(email);setNotice('If an account exists for this email, password reset instructions have been sent.');}
    catch(error){setError(authErrorMessage(error));}
    finally {setPending('');}
  }
  return <div className="login-page">
    <form className="login-card" aria-labelledby="login-title" onSubmit={handleSubmit} aria-busy={!!pending}>
      <div className="login-brand"><Leaf/><span>Agentic Lender</span></div>
      <div className="eyebrow">Welcome back</div>
      <h1 id="login-title">Sign in to<br/><em>Agentic Lender</em></h1>
      <p>Intelligent lending. Cleaner decisions.</p>
      <label>Email<input name="email" type="email" autoComplete="username" required placeholder="you@company.com" value={email} onChange={e=>setEmail(e.target.value)} disabled={!!pending}/></label>
      <label>Password<input name="password" type="password" autoComplete="current-password" required placeholder="Enter your password" value={password} onChange={e=>setPassword(e.target.value)} disabled={!!pending}/></label>
      {(authConfigurationError||error||sessionError||portalNotice)&&<p className="auth-error" role="alert">{authConfigurationError||error||sessionError||portalNotice}</p>}
      {notice&&<p className="auth-notice" role="status">{notice}</p>}
      <button type="submit" className="primary wide" disabled={!!pending||!!authConfigurationError}>{pending==='signin'?'Signing in...':'Sign in'} <ArrowRight size={18}/></button>
      <button type="button" className="text-link" onClick={handleReset} disabled={!!pending||!!authConfigurationError}>{pending==='reset'?'Sending reset instructions...':'Forgot password?'}</button>
    </form>
    <aside className="login-art" aria-label="Brand statement">
      <div className="leaf-blob blob-a"/><div className="leaf-blob blob-b"/><div className="leaf-blob blob-c"/>
      <div className="login-art-copy"><span className="eyebrow">The future of lending</span><h2>Capital for a<br/><em>stronger tomorrow.</em></h2><p>Built for thoughtful underwriting, transparent decisions, and durable outcomes.</p></div>
    </aside>
  </div>
}

function Dashboard({setPage}){
  return <>
    <Hero className="dashboard-hero" eyebrow="Welcome back" title="Dashboard / Origination Pipeline" subtitle="Here’s what’s happening with your loans, brokers, and pipeline today." />
    <section className="three-col-grid">
      <Card title="Notification Board / Info Board" icon={Bell} action="View all">
        <Activity dot="danger" title="Action Required" text="Loan #AL-1042 requires additional documentation (Income Verification)." time="1h ago"/>
        <Activity dot="warn" title="Appraisal received" text="Report uploaded for loan #AL-1036." time="3h ago"/>
        <Activity dot="success" title="Loan approved" text="AL-1028 has been conditionally approved." time="5h ago"/>
        <Activity dot="muted" title="New broker registration" text="BrightPath Capital submitted a registration." time="1d ago"/>
      </Card>
      <Card title="Application / Loan Status" icon={FileText} action="View pipeline" onAction={()=>setPage('pipeline')}>
        <div className="loan-status-layout">
          <Donut value={42} label="Total Applications" segments={[12,14,8,4,4]}/>
          <div className="loan-status-legend" aria-label="Application status breakdown">
            {[['In Review',12,'review'],['Conditionally Approved',14,'conditional'],['Approved',8,'approved'],['Declined',4,'declined'],['Incomplete',4,'incomplete']].map(([label,count,tone])=><div className="loan-status-row" key={label}><span className={`legend-dot ${tone}`}/><span>{label}</span><strong>{count}</strong></div>)}
          </div>
        </div>
        <div className="mini-stats"><div><strong>+18%</strong><span>vs. last month</span></div><div><strong>6.2 days</strong><span>Avg. time to decision</span></div></div>
      </Card>
      <Card title="Broker Status / Information" icon={Users} action="View all">
        {['BrightPath Capital','Greenfield Partners','Summit Property Group','Ridgeview Capital','Lakeside Ventures'].map((x,i)=><div className="broker-row" key={x}><div className="initials">{x.split(' ').map(w=>w[0]).slice(0,2).join('')}</div><div><strong>{x}</strong><span>{12-i*2} active loans</span></div><span className={i===3?'status pending':'status'}>{i===3?'Pending':'Active'}</span></div>)}
      </Card>
    </section>
    <Card className="content-card" title="Relevant Content" icon={FileText} action="View all resources">
      <div className="content-grid">
        {[
          ['Guide','Updated Underwriting Guidelines','Review the latest changes to LTV and DTI requirements.'],
          ['Process','Document Checklist','A complete list of required documents by loan type.'],
          ['Market Insights','Q2 Market Update','Key rate trends and lending opportunities to watch.'],
          ['Training','Broker Portal Training','On-demand onboarding for broker partners.']
        ].map(([tag,title,body],i)=><article className="resource" key={title}><div className={`resource-visual resource-visual-${i+1}`} aria-hidden="true"/><span className="tag">{tag}</span><h3>{title}</h3><p>{body}</p><button className="text-link">{i===1?'View checklist':i===2?'Read insights':i===3?'Watch now':'Read more'} <ChevronRight size={15}/></button></article>)}
      </div>
    </Card>
  </>
}

// Real loan applications from AL-Core (GET /api/v1/loan-applications).
const PIPELINE_PAGE_SIZE=15;
const riskPillClass=tier=>tier?`pill ${tier.toLowerCase()}`:'pill neutral';
const formatPercent=fraction=>`${Math.round(fraction*100)}%`;
const formatDate=iso=>new Intl.DateTimeFormat('en-IE',{day:'2-digit',month:'short',year:'numeric'}).format(new Date(iso));
const formatDateTime=iso=>new Intl.DateTimeFormat('en-IE',{day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit'}).format(new Date(iso));
const DEFAULT_PIPELINE_QUERY={view:'mine',filters:{status:'',riskTier:'',ltvGroup:''},pageNumber:1};

function Pipeline({role,query,setQuery,onOpenApplication}){
  const isBroker=role==='mortgage_broker';
  const {view,filters,pageNumber}=query;
  const [reloadKey,setReloadKey]=useState(0);
  const [result,setResult]=useState({loading:true,error:'',data:null});
  const unclaimedOnly=isBroker&&view==='unclaimed';

  useEffect(()=>{
    let cancelled=false;
    setResult(current=>({...current,loading:true,error:''}));
    listLoanApplications({page:pageNumber,pageSize:PIPELINE_PAGE_SIZE,unclaimedOnly,...filters})
      .then(data=>{if(!cancelled) setResult({loading:false,error:'',data});})
      .catch(error=>{if(!cancelled) setResult({loading:false,error:loanErrorMessage(error),data:null});});
    return ()=>{cancelled=true;};
  },[pageNumber,unclaimedOnly,filters,reloadKey]);

  function changeFilter(key,value){setQuery(q=>({...q,filters:{...q.filters,[key]:value},pageNumber:1}));}
  function changeView(next){setQuery(q=>({...q,view:next,pageNumber:1}));}
  function setPageNumber(update){setQuery(q=>({...q,pageNumber:update(q.pageNumber)}));}
  const rows=result.data?.items||[];
  const filtered=Object.values(filters).some(Boolean);
  const emptyMessage=filtered?'No applications match these filters.'
    :unclaimedOnly?'There are no unclaimed applications right now.'
    :isBroker?'You have not claimed any applications yet. Check the unclaimed applications.'
    :'No applications are assigned to you yet.';

  return <>
    <Hero eyebrow="Pipeline" title="Origination Pipeline" subtitle="Review, filter, and progress mortgage applications." compact/>
    <Card>
      <div className="toolbar sample-toolbar">
        {isBroker&&<div className="sample-segments" role="group" aria-label="Which applications">
          {[['mine','My applications'],['unclaimed','Unclaimed']].map(([value,label])=><button key={value} aria-pressed={view===value} onClick={()=>changeView(value)}>{label}</button>)}
        </div>}
        <select aria-label="Status" value={filters.status} onChange={e=>changeFilter('status',e.target.value)}><option value="">All statuses</option>{LOAN_STATUSES.map(s=><option key={s}>{s}</option>)}</select>
        <select aria-label="Risk" value={filters.riskTier} onChange={e=>changeFilter('riskTier',e.target.value)}><option value="">All risk tiers</option>{RISK_TIERS.map(r=><option key={r}>{r}</option>)}</select>
        <select aria-label="LTV" value={filters.ltvGroup} onChange={e=>changeFilter('ltvGroup',e.target.value)}><option value="">All LTV</option>{Object.entries(LTV_GROUPS).map(([value,label])=><option key={value} value={value}>{label}</option>)}</select>
        <span className="sample-count" aria-live="polite">{result.data?`${result.data.total} application${result.data.total===1?'':'s'}`:''}</span>
      </div>
      {result.error
        ?<div className="empty" role="alert"><p>{result.error}</p><button className="secondary" onClick={()=>setReloadKey(key=>key+1)}><RotateCcw size={16}/>Try again</button></div>
        :<div className="table-wrap" aria-busy={result.loading}><table><thead><tr><th>Application</th><th>Borrower</th><th>Property</th><th>Loan amount</th><th>LTV</th><th>Risk</th><th>Status</th><th>Submitted</th></tr></thead><tbody>
          {rows.map(r=><tr key={r.loanApplicationId} tabIndex="0" aria-label={`Open application ${r.loanApplicationId.slice(0,8)}`}
            onClick={()=>onOpenApplication(r.loanApplicationId)}
            onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();onOpenApplication(r.loanApplicationId);}}}>
            <td title={r.loanApplicationId}>{r.loanApplicationId.slice(0,8)}</td>
            <td>{r.borrowerFullName||'Unknown borrower'}</td>
            <td>{r.propertySpec.county}<small className="sample-table-subtext">{r.propertySpec.propertyType}</small></td>
            <td>{euro(r.loanAmount)}</td>
            <td>{formatPercent(r.ltv)}</td>
            <td><span className={riskPillClass(r.riskTier)}>{r.riskTier||'Not assessed'}</span></td>
            <td><span className="pill neutral">{r.status}</span></td>
            <td>{formatDate(r.createdAt)}</td>
          </tr>)}
          {!rows.length&&<tr><td colSpan={8} className="empty">{result.loading?'Loading applications...':emptyMessage}</td></tr>}
        </tbody></table></div>}
      {result.data?.totalPages>1&&<div className="settings-action-buttons pipeline-pages">
        <button className="secondary" disabled={!result.data.hasPrevious||result.loading} onClick={()=>setPageNumber(n=>n-1)}>Previous</button>
        <span className="sample-count">Page {result.data.page} of {result.data.totalPages}</span>
        <button className="secondary" disabled={!result.data.hasNext||result.loading} onClick={()=>setPageNumber(n=>n+1)}>Next</button>
      </div>}
    </Card>
  </>
}

// One loan application from AL-Core (GET /api/v1/loan-applications/{id}).
function LoanFile({applicationId,currentUid,role,onBack,onOpenAudit}){
  const [reloadKey,setReloadKey]=useState(0);
  const [result,setResult]=useState({loading:Boolean(applicationId),error:'',data:null});
  const [action,setAction]=useState({pending:'',error:''});

  useEffect(()=>{
    if(!applicationId) return;
    let cancelled=false;
    setResult({loading:true,error:'',data:null});
    getLoanApplication(applicationId)
      .then(data=>{if(!cancelled) setResult({loading:false,error:'',data});})
      .catch(error=>{if(!cancelled) setResult({loading:false,error:loanErrorMessage(error,'The application could not be loaded. Please try again.'),data:null});});
    return ()=>{cancelled=true;};
  },[applicationId,reloadKey]);

  // Re-reads the application without a loading screen, e.g. when an AI run moves it to "AI Deliberated".
  function refreshApplication(){
    getLoanApplication(applicationId).then(data=>setResult(current=>({...current,data}))).catch(()=>{});
  }
  const assessment=useLatestAssessment(applicationId,refreshApplication);

  // Claim / return: AL-Core answers with the updated application.
  async function runAction(kind,request){
    setAction({pending:kind,error:''});
    try {
      const updated=await request(applicationId);
      setResult(current=>({...current,data:updated}));
      setAction({pending:'',error:''});
    } catch(error){
      setAction({pending:'',error:actionErrorMessage(error)});
    }
  }

  const backButton=<button className="secondary" onClick={onBack}><ArrowLeft size={16}/>Back to pipeline</button>;
  const hero=<Hero eyebrow="Loan review" title="Loan File / Collateral Assessment" subtitle="Review loan details, borrower finances, property data, and the application's progress." compact/>;
  if(!applicationId||result.loading||result.error) return <>
    {hero}
    <Card><div className="empty" role={result.error?'alert':'status'}>
      <p>{!applicationId?'Choose an application in the Loan Pipeline to see its details.':result.loading?'Loading application...':result.error}</p>
      <div className="settings-action-buttons">{backButton}{result.error&&<button className="secondary" onClick={()=>setReloadKey(key=>key+1)}><RotateCcw size={16}/>Try again</button>}</div>
    </div></Card>
  </>;

  const a=result.data;
  const p=a.propertySpec;
  // AL-Core only returns user IDs, so people are described by their role in this application.
  const assignee=(uid,nobody)=>!uid?nobody:uid===currentUid?'You':'Assigned';
  const actor=uid=>uid==='system'?'System':uid===currentUid?'You':uid===a.borrowerId?'Borrower':uid===a.brokerId?'Broker':uid===a.bankOfficerId?'Underwriter':'Team member';
  return <>
    {hero}
    <div className="loan-header card">
      <div><strong title={a.loanApplicationId}>{a.loanApplicationId.slice(0,8)}</strong><span>{[p.address,p.county].filter(Boolean).join(', ')}</span></div>
      <span className="pill neutral">{a.status}</span>
      <div className="loan-header-actions">{backButton}</div>
    </div>
    <section className="two-col-grid">
      <Card title="Loan Details / Borrower Info" icon={FileText}><KeyValueGrid data={[
        ['Borrower',a.borrowerFullName||'Unknown borrower'],
        ['Loan amount',euro(a.loanAmount)],
        ['Deposit',euro(a.deposit)],
        ['LTV',`${formatPercent(a.ltv)} (${LTV_GROUPS[a.ltvGroup]||a.ltvGroup})`],
        ['Term',`${a.termYears} years`],
        ['First-time buyer',a.firstTimeBuyer?'Yes':'No'],
        ['Annual gross income',euro(a.annualGrossIncome)],
        ['Annual debt repayments',euro(a.annualDebtRepayments)],
      ]}/></Card>
      <Card title="Property Information" icon={Building2}><KeyValueGrid data={[
        ['Property type',p.propertyType],
        ['County',p.county],
        ['Address',p.address||'Not provided'],
        ['Asking price',euro(p.askingPrice)],
        ['Floor area',`${p.floorAreaM2} m²`],
        ['Bedrooms / bathrooms',`${p.bedrooms} / ${p.bathrooms}`],
        ['BER rating',p.ber||'Not provided'],
      ]}/></Card>
      <Card title="AI Assessment" icon={BrainCircuit}>
        <AssessmentSummary application={a} uid={currentUid} assessment={assessment} onOpenAudit={onOpenAudit}/>
      </Card>
      <Card title="Assignment / Decision" icon={UserRoundCheck}>
        <KeyValueGrid data={[
          ['Broker',assignee(a.brokerId,'Unclaimed')],
          ['Underwriter',assignee(a.bankOfficerId,'Not assigned')],
          ['Decision',a.decision?`${a.decision.outcome} (${formatDate(a.decision.decidedAt)})`:'No decision yet'],
          ['Last updated',formatDateTime(a.updatedAt)],
        ]}/>
        {a.decision&&<div className="callout"><strong>Reason</strong><p>{a.decision.reason}</p>
          {a.decision.conditions.length>0&&<ul>{a.decision.conditions.map(condition=><li key={condition}>{condition}</li>)}</ul>}</div>}
        {(canClaim(a,role)||canRelease(a,currentUid))&&<div className="settings-action-buttons card-actions">
          {canClaim(a,role)&&<button className="primary" disabled={!!action.pending} onClick={()=>runAction('claim',claimLoanApplication)}>
            <UserRoundCheck size={16}/>{action.pending==='claim'?'Claiming...':'Claim application'}</button>}
          {canRelease(a,currentUid)&&<button className="secondary" disabled={!!action.pending} onClick={()=>runAction('release',releaseLoanApplication)}>
            <RotateCcw size={16}/>{action.pending==='release'?'Returning...':'Return to unclaimed'}</button>}
        </div>}
        {action.error&&<p className="auth-error" role="alert">{action.error}</p>}
      </Card>
    </section>
    <Card title="Status history" icon={Clock3}>
      <ol className="timeline status-history">{a.statusHistory.map((change,index)=><li key={index}>
        <time dateTime={change.changedAt}>{formatDateTime(change.changedAt)}</time><strong>{change.status}</strong><span>by {actor(change.changedById)}</span>
      </li>)}</ol>
    </Card>
    <LedgerView application={a}/>
  </>;
}

// Latest AI committee run for an application (GET .../assessments/latest). While it is queued or
// running, the page asks again every few seconds: AL-Core checks the AI engine on each request.
// onFinished runs once a run this page watched completes (the application's status has changed).
const ASSESSMENT_POLL_MS=3000;
function useLatestAssessment(applicationId,onFinished){
  const [state,setState]=useState({loading:Boolean(applicationId),error:'',data:null});
  const [starting,setStarting]=useState(false);
  const [startError,setStartError]=useState('');
  const [pollKey,setPollKey]=useState(0);
  const lastStatus=useRef(null);
  const onFinishedRef=useRef(onFinished);
  onFinishedRef.current=onFinished;

  useEffect(()=>{
    if(!applicationId) return;
    let cancelled=false;
    let timer;
    async function check(){
      try {
        const data=await getLatestAssessment(applicationId);
        if(cancelled) return;
        const wasRunning=isRunning({status:lastStatus.current});
        lastStatus.current=data.status;
        setState({loading:false,error:'',data});
        if(isRunning(data)) timer=setTimeout(check,ASSESSMENT_POLL_MS);
        else if(wasRunning) onFinishedRef.current?.(data);
      } catch(error){
        if(cancelled) return;
        // The application itself loaded, so 404 here means it has never been assessed.
        if(error?.status===404) setState({loading:false,error:'',data:null});
        else setState(current=>({...current,loading:false,error:loanErrorMessage(error,'The AI assessment could not be loaded. Please try again.')}));
      }
    }
    check();
    return ()=>{cancelled=true;clearTimeout(timer);};
  },[applicationId,pollKey]);

  async function start(){
    if(starting) return;
    setStarting(true);setStartError('');
    try {
      const data=await requestAssessment(applicationId);
      lastStatus.current=data.status;
      setState({loading:false,error:'',data});
    } catch(error){
      setStartError(actionErrorMessage(error)); // a run the AI engine refused is saved as failed
    } finally {
      setStarting(false);
      setPollKey(key=>key+1);
    }
  }
  return {...state,starting,startError,start,reload:()=>setPollKey(key=>key+1)};
}

function AssessmentRunButton({application,uid,assessment}){
  if(!canRunAssessment(application,uid)||assessment.loading||isRunning(assessment.data)) return null;
  return <button className="primary" disabled={assessment.starting} onClick={assessment.start}>
    <Play size={16}/>{assessment.starting?'Starting...':assessment.data?'Run again':'Run AI assessment'}</button>;
}

// The AI Assessment card on the Loan File.
function AssessmentSummary({application,uid,assessment,onOpenAudit}){
  const run=assessment.data;
  const verdict=run?.decision?.decision;
  const chance=run?.risk?.approval_chance_percent;
  const message=assessment.loading?'Checking for an AI assessment...'
    :isRunning(run)?'The AI committee is deliberating. This updates automatically.'
    :run?.status==='failed'?'The last AI run failed. The AI audit has the technical details.'
    :run?.status==='done'?`Finished ${formatDateTime(run.finishedAt)}${chance!=null?` · approval chance ${chance}%`:''}.`
    :canRunAssessment(application,uid)?'Not assessed yet. Run the AI committee to get a recommendation, risk tier and reasoning.'
    :'Not assessed yet. The assigned broker or underwriter can run the AI committee.';
  return <>
    <div className="assessment-status">
      <span className={riskPillClass(application.riskTier)}>{application.riskTier?`${application.riskTier} risk`:'Not assessed'}</span>
      {verdict&&<span className={`pill ${decisionTone(verdict)}`}>AI: {verdict}</span>}
      {isRunning(run)&&<span className="pill neutral"><Clock3 size={13}/>Deliberating</span>}
    </div>
    <p className="sample-muted" role="status">{message}</p>
    <div className="settings-action-buttons card-actions">
      <AssessmentRunButton application={application} uid={uid} assessment={assessment}/>
      {run&&<button className="secondary" onClick={onOpenAudit}><BrainCircuit size={16}/>Open AI audit</button>}
    </div>
    {assessment.startError&&<p className="auth-error" role="alert">{assessment.startError}</p>}
    {assessment.error&&<p className="auth-error" role="alert">{assessment.error}</p>}
  </>;
}

function FigureGrid({rows}){
  return rows.length?<KeyValueGrid data={rows}/>:<p className="sample-muted">Not available for this run.</p>;
}

// AI Audit & Deliberation Console for the application chosen in the Pipeline.
function AuditPage({applicationId,currentUid,onOpenFile,onOpenPipeline}){
  const [reloadKey,setReloadKey]=useState(0);
  const [app,setApp]=useState({loading:Boolean(applicationId),error:'',data:null});
  useEffect(()=>{
    if(!applicationId) return;
    let cancelled=false;
    setApp({loading:true,error:'',data:null});
    getLoanApplication(applicationId)
      .then(data=>{if(!cancelled) setApp({loading:false,error:'',data});})
      .catch(error=>{if(!cancelled) setApp({loading:false,error:loanErrorMessage(error,'The application could not be loaded. Please try again.'),data:null});});
    return ()=>{cancelled=true;};
  },[applicationId,reloadKey]);
  function refreshApplication(){
    getLoanApplication(applicationId).then(data=>setApp(current=>({...current,data}))).catch(()=>{});
  }
  const assessment=useLatestAssessment(applicationId,refreshApplication);

  const hero=<Hero eyebrow="AI audit" title="AL-AI Audit & Deliberation Console" subtitle="Multi-agent analysis, reasoning, and final recommendation for transparent decisions." compact/>;
  if(!applicationId) return <>{hero}<Card><div className="empty" role="status">
    <p>Choose an application in the Loan Pipeline to see the AI committee's reasoning.</p>
    <div className="settings-action-buttons"><button className="secondary" onClick={onOpenPipeline}><ArrowLeft size={16}/>Go to the pipeline</button></div>
  </div></Card></>;
  if(app.loading||app.error||assessment.loading) return <>{hero}<Card><div className="empty" role={app.error?'alert':'status'}>
    <p>{app.error||'Loading the AI assessment...'}</p>
    {app.error&&<div className="settings-action-buttons"><button className="secondary" onClick={()=>setReloadKey(key=>key+1)}><RotateCcw size={16}/>Try again</button></div>}
  </div></Card></>;

  const a=app.data;
  const run=assessment.data;
  const header=<div className="loan-header card">
    <div><strong title={a.loanApplicationId}>{a.loanApplicationId.slice(0,8)}</strong>
      <span>{[a.borrowerFullName,a.propertySpec.county,euro(a.loanAmount)].filter(Boolean).join(' · ')}</span></div>
    <span className="pill neutral">{a.status}</span>
    <div className="loan-header-actions"><button className="secondary" onClick={onOpenFile}><ArrowLeft size={16}/>Back to loan file</button></div>
  </div>;
  const runControls=<>
    <div className="settings-action-buttons card-actions"><AssessmentRunButton application={a} uid={currentUid} assessment={assessment}/></div>
    {assessment.startError&&<p className="auth-error" role="alert">{assessment.startError}</p>}
    {assessment.error&&<p className="auth-error" role="alert">{assessment.error} <button className="text-link" onClick={assessment.reload}>Try again</button></p>}
  </>;

  if(!run||run.status!=='done'||!run.decision) return <>{hero}{header}
    <Card title="AI committee" icon={BrainCircuit}>
      <p role="status">{!run
        ?(canRunAssessment(a,currentUid)?'This application has not been assessed yet. Run the AI committee to see its recommendation and reasoning.'
          :'This application has not been assessed yet. The assigned broker or underwriter can run the AI committee.')
        :isRunning(run)?'The AI committee is deliberating. This page updates automatically every few seconds.'
        :run.status==='failed'?`The last run failed${run.error?`: ${run.error}`:'.'}`
        :'The run finished without a recommendation.'}</p>
      {runControls}
    </Card>
  </>;

  const verdict=run.decision;
  const tally=tallyVotes(verdict.votes);
  const limits=breachedLimits(run);
  const factors=riskFactors(run.risk);
  const VerdictIcon={Approve:CircleCheckBig,Decline:CircleX,'Conditionally Approve':ClipboardCheck}[verdict.decision]||AlertTriangle;
  return <>
    {hero}{header}
    <section className="two-col-grid">
      <Card title="AI Recommendation" icon={Sparkles}>
        <div className="recommendation"><VerdictIcon/><div><span className="eyebrow">Recommendation</span><h3>{verdict.decision}</h3>{verdict.reason&&<p>{verdict.reason}</p>}</div></div>
        {verdict.automatic&&<p className="sample-muted">Declined automatically: a hard lending limit was broken, so the AI models were not asked.</p>}
        {verdict.conditions.length>0&&<div className="callout"><strong>Conditions</strong><ul>{verdict.conditions.map((item,index)=><li key={index}>{item}</li>)}</ul></div>}
        {verdict.keyRisks.length>0&&<div className="callout"><strong>Key risks</strong><ul>{verdict.keyRisks.map((item,index)=><li key={index}>{item}</li>)}</ul></div>}
        {runControls}
      </Card>
      <Card title="Committee votes" icon={Users}>
        {verdict.votes.length?<>
          <p className="sample-muted">{Object.entries(tally).map(([decision,count])=>`${count} × ${decision}`).join(' · ')}</p>
          <ul className="vote-list">{verdict.votes.map((vote,index)=><li key={`${vote.provider}-${index}`}>
            <strong>{providerLabel(vote.provider)}</strong>
            <span className={`pill ${decisionTone(vote.decision)}`}>{vote.decision||'Unavailable'}</span>
            <span>{vote.reason||'No answer from this model.'}</span>
          </li>)}</ul>
        </>:<p className="sample-muted">{verdict.automatic?'No votes: the application was declined automatically.':'No AI model returned a vote.'}</p>}
      </Card>
    </section>
    <section className="three-col-grid">
      <Card title="Affordability" icon={WalletCards}><FigureGrid rows={affordabilityRows(run.affordability)}/></Card>
      <Card title="Collateral" icon={Building2}><FigureGrid rows={collateralRows(run.collateral)}/></Card>
      <Card title="Risk" icon={ShieldCheck}><FigureGrid rows={riskRows(run.risk)}/>
        {factors.length>0&&<ul className="factor-list">{factors.map(factor=><li key={factor.label}>
          <span>{factor.label}</span><strong>{factor.value}</strong><small>{factor.points} pts</small>
        </li>)}</ul>}
      </Card>
    </section>
    {limits.length>0&&<Card title="Lending limits broken" icon={AlertTriangle}><ul className="limit-list">{limits.map(limit=><li key={limit}>{limit}</li>)}</ul></Card>}
    <Card title="Reasoning / Decision Trail" icon={FileText}>
      {run.steps.length?<ol className="timeline status-history">{run.steps.map(step=><li key={step.stepNumber}>
        <time>Step {step.stepNumber}</time><strong>{agentLabel(step.agent)}</strong><span>{step.summary}</span>
      </li>)}</ol>:<p className="sample-muted">No reasoning steps were recorded for this run.</p>}
      <p className="sample-muted audit-footnote">Finished {formatDateTime(run.finishedAt)} · interest rate used {run.ratePercent}%</p>
    </Card>
  </>;
}

function Stress({scenario,setScenario}){
  const [simulationRun,setSimulationRun] = useState(0);
  const points = useMemo(()=>{
    const base=[20,30,42,66,84,98];
    const stressed=base.map((v,i)=>Math.max(8,Math.round(v*(1-(scenario.rate*0.08)) + scenario.price*0.35 - i*2)));
    return {base,stressed};
  },[scenario]);
  return <>
    <Hero eyebrow="Stress testing" title="Macro Stress-Testing Simulator" subtitle="Model the impact of macroeconomic scenarios on your loan portfolio." compact/>
    <Card title="Scenario Controls" icon={Gauge}><div className="control-grid"><label>Economic scenario<select value={scenario.economic} onChange={e=>setScenario({...scenario,economic:e.target.value})}><option>Recession</option><option>Base Case</option><option>Expansion</option></select></label><label>Interest rate change<input type="number" value={scenario.rate} step="0.5" onChange={e=>setScenario({...scenario,rate:+e.target.value})}/></label><label>Home price change<input type="number" value={scenario.price} step="5" onChange={e=>setScenario({...scenario,price:+e.target.value})}/></label><button className="primary" onClick={()=>setSimulationRun(run=>run+1)}><Play size={17}/>Run simulation</button></div></Card>
    <Card title="Portfolio Performance Under Stress Scenario" icon={LineChart}><LineChartFlat key={simulationRun} base={points.base} stressed={points.stressed}/></Card>
    <div className="four-col-grid"><MetricCard icon={ShieldCheck} label="Default Probability" value="12.5%" delta="+6.8% vs base"/><MetricCard icon={Home} label="LTV Impact" value="+18%" delta="vs base"/><MetricCard icon={WalletCards} label="DSCR Impact" value="-0.35x" delta="vs base"/><MetricCard icon={TrendingUp} label="Portfolio Impact" value="-$12.4M" delta="vs base"/></div>
  </>
}

function Decision({decision,setDecision}){
  return <>
    <Hero eyebrow="Final review" title="Final Decision & On-Chain Settlement" subtitle="Review the application, make the final underwriting decision, and initiate settlement." compact/>
    <section className="two-col-grid">
      <Card title="Application Summary" icon={ClipboardCheck}><KeyValueGrid data={[['Loan number','#AL-1042'],['Borrower','BrightPath Capital'],['Property','1234 Market St'],['Loan amount','$2,500,000'],['Loan type','Commercial Real Estate'],['LTV','65%'],['DSCR','1.28x'],['Purpose','Acquisition']]}/></Card>
      <Card title="AI Recommendation" icon={Sparkles}><div className="recommendation"><CircleCheckBig/><div><span className="eyebrow">Recommendation</span><h3>Approve</h3><p>Strong profile, stable cash flow, and favorable collateral.</p></div></div><Donut value={85} label="AI confidence" segments={[85,15]}/></Card>
      <Card title="Underwriter Decision" icon={UserRoundCheck}><div className="decision-grid">{['Approve','Conditionally Approve','Decline'].map(x=><button className={decision===x?'decision active':'decision'} onClick={()=>setDecision(x)} key={x}>{x==='Approve'?<CircleCheckBig/>:x==='Decline'?<CircleX/>:<FileText/>}<span>{x}</span></button>)}</div></Card>
      <Card title="Underwriter Notes" icon={FileText}><textarea rows="6" defaultValue="Strong borrower profile with consistent cash flows. Recommend approval and proceed with on-chain settlement."/></Card>
    </section>
    <section className="two-col-grid">
      <Card title="Blockchain Record / Settlement Status" icon={Link2}><div className="stepper">{['Initiated','Validated','On Chain','Completed'].map((x,i)=><div className={i<3?'step done':'step'} key={x}><span>{i<3?'✓':i+1}</span><small>{x}</small></div>)}</div><KeyValueGrid data={[['Transaction hash','0x8f3a...d6e4'],['Network','Ethereum Mainnet'],['Block','19,482,331'],['Status','Processing']]}/></Card>
      <Card title="Export / Actions" icon={Download}><div className="action-stack"><button className="secondary"><Download/>Export PDF</button><button className="primary"><Link2/>Send to Blockchain Settlement</button><button className="secondary"><FileText/>Generate Closing Package</button><button className="secondary"><Users/>Notify Stakeholders</button></div></Card>
    </section>
  </>
}

function Hero({eyebrow,title,subtitle,compact=false,className=''}){return <section className={`hero ${compact?'compact':''} ${className}`}><div><span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p>{subtitle}</p></div><div className="botanical-mark" aria-hidden="true"><Leaf/><Leaf/><Leaf/></div></section>}
function Card({title,icon:Icon,action,onAction,children,className=''}){return <section className={`card ${className}`}><header>{title&&<h2>{Icon&&<span className="icon-chip"><Icon size={18}/></span>}{title}</h2>}{action&&<button className="text-link" onClick={onAction}>{action}<ChevronRight size={15}/></button>}</header>{children}</section>}
function Activity({dot,title,text,time}){return <div className="activity"><i className={`dot ${dot}`}/><div><strong>{title}</strong><span>{text}</span></div><time>{time}</time></div>}
function Donut({value,label,segments}){
  const total=segments.reduce((sum,count)=>sum+count,0);
  let cumulative=0;
  const colors=['var(--chart-review)','var(--chart-conditional)','var(--chart-approved)','var(--chart-declined)','var(--chart-incomplete)'];
  const stops=segments.map((count,index)=>{
    const start=total ? cumulative/total*100 : 0;
    cumulative+=count;
    const end=total ? cumulative/total*100 : 0;
    return `${colors[index%colors.length]} ${start}% ${end}%`;
  }).join(',');
  return <div className="donut-wrap"><div className="donut" style={{'--donut-fill':total ? `conic-gradient(${stops})` : 'var(--line)'}}><div><strong>{value}</strong><span>{label}</span></div></div></div>;
}
function KeyValueGrid({data}){return <dl className="kv-grid">{data.map(([k,v])=><div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}</dl>}
function MetricCard({icon:Icon,label,value,delta}){return <Card><div className="metric-card"><span className="icon-chip"><Icon size={19}/></span><span>{label}</span><strong>{value}</strong><small>{delta}</small></div></Card>}
function LineChartFlat({base,stressed}){
  const revealId=useId();
  const width=720,height=250,pad=28,max=110;
  const x=(index,length)=>pad+index*((width-pad*2)/(length-1));
  const y=value=>height-pad-(value/max)*(height-pad*2);
  const pts=values=>values.map((value,index)=>`${x(index,values.length)},${y(value)}`).join(' ');
  const basePoints=pts(base),stressedPoints=pts(stressed);
  return <div className="line-chart-wrap">
    <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Base case and stress scenario line chart">
      <defs><clipPath id={revealId} clipPathUnits="userSpaceOnUse">
        <rect key={`${basePoints}|${stressedPoints}`} className="chart-reveal" width={width} height={height}/>
      </clipPath></defs>
      <line x1={pad} x2={pad} y1={pad} y2={height-pad}/>
      <line x1={pad} x2={width-pad} y1={height-pad} y2={height-pad}/>
      <g clipPath={`url(#${revealId})`}>
        <polyline className="line base" points={basePoints}/>
        <polyline className="line stressed" points={stressedPoints}/>
        {base.map((value,index)=><circle key={'b'+index} className="pt base" cx={x(index,base.length)} cy={y(value)} r="4"/>)}
        {stressed.map((value,index)=><circle key={'s'+index} className="pt stressed" cx={x(index,stressed.length)} cy={y(value)} r="4"/>)}
      </g>
    </svg>
    <div className="chart-legend"><span><i className="legend green"/>Base case</span><span><i className="legend sage"/>Stress scenario</span></div>
  </div>;
}
const sampleBrokers = [
  {name:'BrightPath Capital',contact:'Emma Walsh',city:'Cork',loans:12,volume:2480000,approval:83,status:'Active',email:'emma@brightpath.example'},
  {name:'Greenfield Partners',contact:'Conor Murphy',city:'Dublin',loans:10,volume:1920000,approval:80,status:'Active',email:'conor@greenfield.example'},
  {name:'Summit Property Group',contact:'Aoife Kelly',city:'Galway',loans:8,volume:1640000,approval:75,status:'Active',email:'aoife@summit.example'},
  {name:'Ridgeview Capital',contact:'Daniel Byrne',city:'Limerick',loans:6,volume:980000,approval:67,status:'Pending',email:'daniel@ridgeview.example'},
  {name:'Lakeside Ventures',contact:'Niamh Ryan',city:'Waterford',loans:4,volume:720000,approval:75,status:'Active',email:'niamh@lakeside.example'},
];
const euro = value => new Intl.NumberFormat('en-IE',{style:'currency',currency:'EUR',maximumFractionDigits:0}).format(value);

function Brokers(){
  const [query,setQuery]=useState('');
  const [status,setStatus]=useState('All');
  const [selected,setSelected]=useState(null);
  const rows=sampleBrokers.filter(b=>(status==='All'||b.status===status)&&`${b.name} ${b.contact} ${b.city}`.toLowerCase().includes(query.toLowerCase().trim()));
  return <>
    <Hero eyebrow="Sample portfolio" title="Brokers" subtitle="Partner relationships, application activity, and lending performance." compact/>
    <div className="four-col-grid sample-metrics">
      <MetricCard icon={Users} label="Broker partners" value={sampleBrokers.length} delta="Across five Irish cities"/>
      <MetricCard icon={CheckCircle2} label="Active partners" value={sampleBrokers.filter(b=>b.status==='Active').length} delta="One partner awaiting review"/>
      <MetricCard icon={FileText} label="Active applications" value={sampleBrokers.reduce((sum,b)=>sum+b.loans,0)} delta="Across all partner accounts"/>
      <MetricCard icon={CircleDollarSign} label="Pipeline value" value={euro(sampleBrokers.reduce((sum,b)=>sum+b.volume,0))} delta="Requested financing"/>
    </div>
    <Card title="Partner directory" icon={Users}>
      <div className="toolbar sample-toolbar"><div className="search small"><Search size={17}/><input aria-label="Search brokers" placeholder="Search partners, contacts, or cities" value={query} onChange={e=>setQuery(e.target.value)}/></div><select aria-label="Broker status" value={status} onChange={e=>setStatus(e.target.value)}>{['All','Active','Pending'].map(s=><option key={s} value={s}>{s==='All'?'All statuses':s}</option>)}</select><span className="sample-count" aria-live="polite">{rows.length} partners</span></div>
      <div className="table-wrap"><table><thead><tr><th>Partner</th><th>Contact</th><th>City</th><th>Applications</th><th>Pipeline value</th><th>Status</th></tr></thead><tbody>{rows.map(b=><tr key={b.name}><td><button className="text-link" onClick={()=>setSelected(b)} aria-expanded={selected===b} aria-controls="broker-profile">{b.name}<ChevronRight size={14}/></button></td><td>{b.contact}</td><td>{b.city}</td><td>{b.loans}</td><td>{euro(b.volume)}</td><td><span className={`pill ${b.status==='Active'?'low':'medium'}`}>{b.status}</span></td></tr>)}{!rows.length&&<tr><td colSpan={6} className="empty">No partners match these filters.</td></tr>}</tbody></table></div>
    </Card>
    {selected&&<section id="broker-profile" className="sample-detail" aria-label="Broker profile"><header><h2>{selected.name}</h2><button className="icon-btn" aria-label="Close broker profile" onClick={()=>setSelected(null)}><X size={18}/></button></header><KeyValueGrid data={[
      ['Primary contact',selected.contact],['Contact email',selected.email],['Office',selected.city],['Approval rate',`${selected.approval}%`],['Active applications',selected.loans],['Onboarding',selected.status==='Active'?'Complete':'Compliance review pending'],
    ]}/></section>}
  </>;
}

const sampleMonths = [
  {month:'May',applications:24,approved:17,funded:2100000},
  {month:'Jun',applications:28,approved:20,funded:2450000},
  {month:'Jul',applications:31,approved:23,funded:2800000},
  {month:'Aug',applications:35,approved:26,funded:3100000},
  {month:'Sep',applications:38,approved:29,funded:3450000},
  {month:'Oct',applications:42,approved:32,funded:3900000},
];
function Analytics(){
  const [period,setPeriod]=useState(6);
  const months=sampleMonths.slice(-period);
  const applications=months.reduce((sum,m)=>sum+m.applications,0);
  const approved=months.reduce((sum,m)=>sum+m.approved,0);
  const max=Math.max(...months.map(m=>m.applications));
  const riskCounts=['Low','Medium','High'].map(risk=>applicationRows.filter(row=>row.risk===risk).length);
  return <>
    <Hero eyebrow="Sample portfolio / 2026" title="Analytics" subtitle="Application trends, funding activity, and the current portfolio risk profile." compact/>
    <div className="sample-period"><span>Reporting period</span><div className="sample-segments" role="group" aria-label="Reporting period">{[3,6].map(value=><button key={value} aria-pressed={period===value} onClick={()=>setPeriod(value)}>Last {value} months</button>)}</div></div>
    <div className="four-col-grid sample-metrics">
      <MetricCard icon={FileText} label="Applications received" value={applications} delta={`${months[0].month} to Oct 2026`}/>
      <MetricCard icon={CircleCheckBig} label="Applications approved" value={approved} delta={`${Math.round(approved/applications*100)}% approval rate`}/>
      <MetricCard icon={WalletCards} label="Total funded" value={euro(months.reduce((sum,m)=>sum+m.funded,0))} delta="Completed loan disbursements"/>
      <MetricCard icon={TrendingUp} label="Latest monthly growth" value="+11%" delta="October applications vs September"/>
    </div>
    <section className="two-col-grid sample-analytics">
      <Card title="Application activity" icon={BarChart3}>
        <div className="sample-chart" role="img" aria-label={months.map(m=>`${m.month}: ${m.applications} applications, ${m.approved} approved`).join('; ')}>
          {months.map(m=><div className="sample-chart-column" key={m.month}><strong>{m.applications}</strong><div className="sample-bar-track"><div className="sample-bar received" style={{height:`${m.applications/max*100}%`}}/><div className="sample-bar approved" style={{height:`${m.approved/max*100}%`}}/></div><span>{m.month}</span></div>)}
        </div>
        <div className="chart-legend"><span><i className="legend green"/>Received</span><span><i className="legend sage"/>Approved</span></div>
      </Card>
      <Card title="Current pipeline risk" icon={ShieldCheck}>
        <p className="sample-muted">Risk distribution for the {applicationRows.length} listed applications.</p>
        <ul className="sample-risk-list">{['Low','Medium','High'].map((risk,index)=><li key={risk}><span className={`pill ${risk.toLowerCase()}`}>{risk}</span><div className="sample-risk-track"><span style={{width:`${riskCounts[index]/applicationRows.length*100}%`}}/></div><strong>{riskCounts[index]}</strong></li>)}</ul>
        <p className="sample-muted">{Math.round(riskCounts[0]/applicationRows.length*100)}% of the current pipeline is rated low risk.</p>
      </Card>
    </section>
    <Card title="Monthly performance" icon={LineChart}><div className="table-wrap"><table><thead><tr><th>Month</th><th>Applications</th><th>Approved</th><th>Approval rate</th><th>Funded</th></tr></thead><tbody>{months.map(m=><tr key={m.month}><td>{m.month} 2026</td><td>{m.applications}</td><td>{m.approved}</td><td>{Math.round(m.approved/m.applications*100)}%</td><td>{euro(m.funded)}</td></tr>)}</tbody></table></div></Card>
  </>;
}

const sampleDocuments = [
  {id:'DOC-001',name:'Application summary',loan:'AL-1042',borrower:'BrightPath Capital',category:'Application',status:'Verified',date:'10 Oct 2026',body:'Sample application summary\nRequested finance: EUR 420,000\nProperty location: Cork\nApplication received and assigned for review.'},
  {id:'DOC-002',name:'Income verification checklist',loan:'AL-1042',borrower:'BrightPath Capital',category:'Income',status:'Action required',date:'11 Oct 2026',body:'Sample income verification checklist\nOutstanding: recent income statements and supporting account records.\nThe review team will confirm the documents required for this application.'},
  {id:'DOC-003',name:'Valuation review notes',loan:'AL-1041',borrower:'Greenfield Partners',category:'Property',status:'Under review',date:'09 Oct 2026',body:'Sample valuation review\nProperty location: Dublin\nReview of the submitted valuation is in progress.\nComparable evidence and property condition await confirmation.'},
  {id:'DOC-004',name:'Identity review record',loan:'AL-1040',borrower:'Summit Property Group',category:'Identity',status:'Verified',date:'08 Oct 2026',body:'Sample identity review record\nApplicant details checked for consistency.\nNo identity documents or personal identifiers are included in this sample.'},
  {id:'DOC-005',name:'Conditional approval summary',loan:'AL-1039',borrower:'Ridgeview Capital',category:'Decision',status:'Verified',date:'07 Oct 2026',body:'Sample conditional approval summary\nRequested finance: EUR 250,000\nProperty location: Limerick\nOutstanding conditions will be confirmed by the lending team.\nThis sample is not a lending offer.'},
  {id:'DOC-006',name:'Property information checklist',loan:'AL-1038',borrower:'Lakeside Ventures',category:'Property',status:'Under review',date:'06 Oct 2026',body:'Sample property information checklist\nProperty location: Waterford\nProperty details received.\nSupporting valuation and title information are awaiting review.'},
];
function downloadSampleDocument(doc){
  const blob=new Blob([`${doc.name}\n${doc.id} | ${doc.loan}\n${doc.borrower}\nUpdated: ${doc.date}\nStatus: ${doc.status}\n\n${doc.body}\n`],{type:'text/plain;charset=utf-8'});
  const url=URL.createObjectURL(blob);
  const link=document.createElement('a');
  link.href=url;
  link.download=`${doc.id}-${doc.loan}.txt`;
  link.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function Documents(){
  const [query,setQuery]=useState('');
  const [status,setStatus]=useState('All');
  const [selected,setSelected]=useState(null);
  const rows=sampleDocuments.filter(doc=>(status==='All'||doc.status===status)&&`${doc.name} ${doc.loan} ${doc.borrower} ${doc.category}`.toLowerCase().includes(query.toLowerCase().trim()));
  return <>
    <Hero eyebrow="Sample document library" title="Documents" subtitle="Application records, verification checklists, and property review notes." compact/>
    <div className="four-col-grid sample-metrics">
      {[['Documents',sampleDocuments.length,FileText],['Verified',sampleDocuments.filter(d=>d.status==='Verified').length,ShieldCheck],['Under review',sampleDocuments.filter(d=>d.status==='Under review').length,Clock3],['Action required',sampleDocuments.filter(d=>d.status==='Action required').length,AlertTriangle]].map(([label,value,Icon])=><MetricCard key={label} icon={Icon} label={label} value={value} delta="Sample library"/>)}
    </div>
    <Card title="Document library" icon={FileText}>
      <div className="toolbar sample-toolbar"><div className="search small"><Search size={17}/><input aria-label="Search documents" placeholder="Search documents, borrowers, or loan IDs" value={query} onChange={e=>setQuery(e.target.value)}/></div><select aria-label="Document status" value={status} onChange={e=>setStatus(e.target.value)}>{['All','Verified','Under review','Action required'].map(s=><option key={s} value={s}>{s==='All'?'All statuses':s}</option>)}</select><span className="sample-count" aria-live="polite">{rows.length} documents</span></div>
      <div className="table-wrap"><table><thead><tr><th>Document</th><th>Loan / borrower</th><th>Category</th><th>Status</th><th>Updated</th><th>Download</th></tr></thead><tbody>{rows.map(doc=><tr key={doc.id}><td><button className="text-link" onClick={()=>setSelected(doc)} aria-expanded={selected===doc} aria-controls="document-preview">{doc.name}<ChevronRight size={14}/></button></td><td>{doc.loan}<small className="sample-table-subtext">{doc.borrower}</small></td><td>{doc.category}</td><td><span className={`pill ${doc.status==='Verified'?'low':doc.status==='Action required'?'medium':'neutral'}`}>{doc.status}</span></td><td>{doc.date}</td><td><button className="icon-btn" aria-label={`Download ${doc.name}`} title="Download sample text file" onClick={()=>downloadSampleDocument(doc)}><Download size={18}/></button></td></tr>)}{!rows.length&&<tr><td colSpan={6} className="empty">No documents match these filters.</td></tr>}</tbody></table></div>
    </Card>
    {selected&&<section id="document-preview" className="sample-detail" aria-label="Document preview"><header><div><span className="eyebrow">{selected.id} / {selected.loan}</span><h2>{selected.name}</h2></div><button className="icon-btn" aria-label="Close document preview" onClick={()=>setSelected(null)}><X size={18}/></button></header><pre className="sample-document-body">{selected.body}</pre><button className="secondary" onClick={()=>downloadSampleDocument(selected)}><Download size={17}/>Download sample</button></section>}
  </>;
}

const preferencesKey='agentic-lender.preferences.v1';
// Account details (name, email, role) come from AL-Core; only these local preferences are stored.
const defaultPreferences={
  organisation:'Agentic Lender',
  applicationUpdates:true,documentRequests:true,weeklySummary:false,
  density:'comfortable',reduceMotion:false,
};
function loadPreferences(){
  try {
    const saved=JSON.parse(localStorage.getItem(preferencesKey));
    if(!saved||typeof saved!=='object') return {...defaultPreferences};
    const result={...defaultPreferences};
    if(typeof saved.organisation==='string'&&saved.organisation.trim()) result.organisation=saved.organisation.trim().slice(0,80);
    for(const key of ['applicationUpdates','documentRequests','weeklySummary','reduceMotion']){
      if(typeof saved[key]==='boolean') result[key]=saved[key];
    }
    if(['comfortable','compact'].includes(saved.density)) result.density=saved.density;
    return result;
  } catch { return {...defaultPreferences}; }
}
function SettingsPage({preferences,onSave,profile}){
  const [draft,setDraft]=useState(()=>({...preferences}));
  const [notice,setNotice]=useState('');
  const [error,setError]=useState('');
  const dirty=Object.keys(defaultPreferences).some(key=>draft[key]!==preferences[key]);
  function change(key,value){setDraft(current=>({...current,[key]:value}));setNotice('');setError('');}
  function save(event){
    event.preventDefault();
    const next={...draft,organisation:draft.organisation.trim()};
    if(!next.organisation){setError('Enter an organisation.');return;}
    try {localStorage.setItem(preferencesKey,JSON.stringify(next));}
    catch {setError('Settings could not be saved in this browser. Please try again.');return;}
    onSave(next);setDraft(next);setError('');setNotice('Settings saved in this browser.');
  }
  return <>
    <Hero eyebrow="Sample workspace" title="Settings" subtitle="Your profile, notification preferences, and workspace appearance." compact/>
    <form className="settings-form" onSubmit={save}>
      <section className="settings-section" aria-labelledby="settings-profile-title">
        <div className="settings-section-title"><UserRoundCheck size={21}/><div><h2 id="settings-profile-title">Profile</h2><p>Account details from AL-Core. Organisation is saved in this browser.</p></div></div>
        <div className="settings-fields">
          <label>Full name<input name="name" value={profile?.full_name||''} placeholder="Not set" readOnly/></label>
          <label>Email address<input name="email" type="email" value={profile?.email||''} readOnly/></label>
          <label>Phone<input name="phone" value={profile?.phone||''} placeholder="Not set" readOnly/></label>
          <label>Account role<input value={profile?roleLabel(profile.role):''} readOnly/></label>
          <label>Organisation<input name="organisation" autoComplete="organization" maxLength={80} required value={draft.organisation} onChange={e=>change('organisation',e.target.value)}/></label>
        </div>
      </section>
      <section className="settings-section" aria-labelledby="settings-notifications-title">
        <div className="settings-section-title"><Bell size={21}/><div><h2 id="settings-notifications-title">Notifications</h2><p>Demo notification preferences.</p></div></div>
        <div className="settings-options">{[
          ['applicationUpdates','Application updates','Decisions and changes to application status.'],
          ['documentRequests','Document requests','Missing documents and verification requests.'],
          ['weeklySummary','Weekly summary','A weekly overview of pipeline activity.'],
        ].map(([key,title,description])=><label className="settings-toggle" key={key}><span><strong>{title}</strong><small>{description}</small></span><input type="checkbox" role="switch" checked={draft[key]} onChange={e=>change(key,e.target.checked)} aria-label={title}/></label>)}</div>
      </section>
      <section className="settings-section" aria-labelledby="settings-workspace-title">
        <div className="settings-section-title"><Settings size={21}/><div><h2 id="settings-workspace-title">Workspace</h2><p>Display and motion preferences.</p></div></div>
        <div className="settings-options">
          <fieldset className="settings-density"><legend>Table density</legend><div className="sample-segments">{['comfortable','compact'].map(value=><label key={value}><input type="radio" name="density" value={value} checked={draft.density===value} onChange={()=>change('density',value)}/><span>{value==='compact'?'Compact':'Comfortable'}</span></label>)}</div></fieldset>
          <label className="settings-toggle"><span><strong>Reduce motion</strong><small>Limit page transitions and chart animations.</small></span><input type="checkbox" role="switch" aria-label="Reduce motion" checked={draft.reduceMotion} onChange={e=>change('reduceMotion',e.target.checked)}/></label>
        </div>
      </section>
      <div className="settings-actions"><div className="settings-feedback"><span role="status">{notice||(dirty?'Unsaved changes':'All changes saved')}</span>{error&&<span role="alert">{error}</span>}</div><div className="settings-action-buttons"><button type="button" className="secondary" disabled={!dirty} onClick={()=>{setDraft({...preferences});setNotice('Changes discarded.');setError('');}}><RotateCcw size={16}/>Reset changes</button><button type="submit" className="primary" disabled={!dirty}><Save size={16}/>Save changes</button></div></div>
    </form>
  </>;
}

createRoot(document.getElementById('root')).render(<App/>);

