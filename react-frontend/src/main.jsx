import React, {useEffect, useId, useMemo, useState} from 'react';
import {createRoot} from 'react-dom/client';
import {
  Home, FileText, Users, BarChart3, Settings, LogOut, Search, Bell,
  Leaf, ChevronRight, CheckCircle2, AlertTriangle, CircleDollarSign,
  Building2, ShieldCheck, BrainCircuit, TrendingUp, Download, Link2,
  Play, UserRoundCheck, Gauge, LineChart, Menu, X, Clock3, ArrowRight,
  CircleCheckBig, CircleX, ClipboardCheck, Sparkles, Landmark, WalletCards,
  Save, RotateCcw
} from 'lucide-react';
import './styles.css';
import './aero.css';

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

function App(){
  const [preferences,setPreferences]=useState(loadPreferences);
  useEffect(()=>{
    document.documentElement.dataset.density=preferences.density;
    document.documentElement.dataset.reduceMotion=String(preferences.reduceMotion);
  },[preferences.density,preferences.reduceMotion]);
  const [page,setPage] = useState('dashboard');
  const [mobileOpen,setMobileOpen] = useState(false);
  const [role,setRole] = useState('Underwriter');
  const [decision,setDecision] = useState('Approve');
  const [scenario,setScenario] = useState({economic:'Recession', rate:2, price:-20});

  if(page==='login') return <Login setPage={setPage} role={role} setRole={setRole}/>;

  return <div className="app-shell">
    <Sidebar page={page} setPage={setPage} mobileOpen={mobileOpen} setMobileOpen={setMobileOpen}/>
    <div className="main-shell">
      <Topbar setMobileOpen={setMobileOpen} preferences={preferences}/>
      <main key={page} id="main-content" className="page-wrap">
        {page==='dashboard' && <Dashboard setPage={setPage}/>} 
        {page==='pipeline' && <Pipeline setPage={setPage}/>} 
        {page==='loan' && <LoanFile setPage={setPage}/>} 
        {page==='audit' && <Audit/>}
        {page==='stress' && <Stress scenario={scenario} setScenario={setScenario}/>} 
        {page==='decision' && <Decision decision={decision} setDecision={setDecision}/>} 
        {page==='brokers' && <Brokers/>}
        {page==='analytics' && <Analytics/>}
        {page==='documents' && <Documents/>}
        {page==='settings' && <SettingsPage preferences={preferences} onSave={setPreferences}/>}
      </main>
    </div>
  </div>
}

function Sidebar({page,setPage,mobileOpen,setMobileOpen}){
  return <>
    <aside className={`sidebar ${mobileOpen?'open':''}`} aria-label="Primary navigation">
      <div className="brand"><Leaf size={25}/><span>Agentic Lender</span></div>
      <nav>
        {navItems.map(([id,label,Icon])=><button key={id} className={page===id?'active':''} onClick={()=>{setPage(id);setMobileOpen(false)}}><Icon size={19}/><span>{label}</span></button>)}
        <button className={page==='audit'?'active':''} onClick={()=>{setPage('audit');setMobileOpen(false)}}><BrainCircuit size={19}/>AI Audit</button>
        <button className={page==='stress'?'active':''} onClick={()=>{setPage('stress');setMobileOpen(false)}}><Gauge size={19}/>Stress Testing</button>
        <button className={page==='decision'?'active':''} onClick={()=>{setPage('decision');setMobileOpen(false)}}><Link2 size={19}/>Settlement</button>
        <button className={page==='settings'?'active':''} onClick={()=>{setPage('settings');setMobileOpen(false)}}><Settings size={19}/><span>Settings</span></button>
      </nav>
      <div className="sidebar-quote">“Clear lending.<br/>Stronger outcomes.”</div>
      <button className="logout" onClick={()=>setPage('login')}><LogOut size={19}/>Logout</button>
    </aside>
    {mobileOpen && <button className="backdrop" aria-label="Close menu" onClick={()=>setMobileOpen(false)}/>} 
  </>
}

function Topbar({setMobileOpen,preferences}){
  return <header className="topbar">
    <button className="icon-btn mobile-only" aria-label="Open menu" onClick={()=>setMobileOpen(true)}><Menu/></button>
    <div className="search"><Search size={18}/><input aria-label="Search" placeholder="Search loans, brokers, or documents..."/></div>
    <div className="top-actions"><button className="icon-btn" aria-label="Notifications"><Bell/></button><div className="avatar" aria-hidden="true">{preferences.name.split(/\s+/).filter(Boolean).map(part=>part[0]).slice(0,2).join('')}</div><div className="user-meta"><strong>{preferences.name}</strong><span>Underwriter</span></div></div>
  </header>
}

function Login({setPage,role,setRole}){
  return <div className="login-page">
    <section className="login-card" aria-labelledby="login-title">
      <div className="login-brand"><Leaf/><span>Agentic Lender</span></div>
      <div className="eyebrow">Welcome back</div>
      <h1 id="login-title">Sign in to<br/><em>Agentic Lender</em></h1>
      <p>Intelligent lending. Cleaner decisions.</p>
      <label>Email<input type="email" placeholder="you@company.com"/></label>
      <label>Password<input type="password" placeholder="Enter your password"/></label>
      <label>Select role<select value={role} onChange={e=>setRole(e.target.value)}><option>Underwriter</option><option>Mortgage Broker</option></select></label>
      <button className="primary wide" onClick={()=>setPage('dashboard')}>Sign in <ArrowRight size={18}/></button>
      <button className="text-link">Forgot password?</button>
    </section>
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

function Pipeline({setPage}){
  return <>
    <Hero eyebrow="Pipeline" title="Origination Pipeline" subtitle="Review, filter, and progress mortgage and HELOC applications." compact/>
    <Card>
      <div className="toolbar"><div className="search small"><Search size={17}/><input placeholder="Search applications..."/></div><select><option>Status</option><option>Applied</option><option>Under Review</option></select><select><option>Risk</option><option>Low</option><option>Medium</option><option>High</option></select><button className="primary">New application</button></div>
      <div className="table-wrap"><table><thead><tr><th>ID</th><th>Borrower</th><th>Property</th><th>Amount</th><th>LTV</th><th>Risk</th><th>Status</th></tr></thead><tbody>{applicationRows.map(r=><tr key={r.id} tabIndex="0" onClick={()=>setPage('loan')}><td>{r.id}</td><td>{r.borrower}</td><td>{r.property}</td><td>{r.amount}</td><td>{r.ltv}</td><td><span className={`pill ${r.risk.toLowerCase()}`}>{r.risk}</span></td><td><span className="pill neutral">{r.status}</span></td></tr>)}</tbody></table></div>
    </Card>
  </>
}

function LoanFile({setPage}){
  return <>
    <Hero eyebrow="Loan review" title="Loan File / Collateral Assessment" subtitle="Review loan details, borrower information, property data, and valuation signals." compact/>
    <div className="loan-header card"><div><strong>AL-1234</strong><span>123 Main St, Austin TX</span></div><span className="pill neutral">In Review</span><div className="tabs"><button className="active">Overview</button><button>Property</button><button>Borrower</button><button>Documents</button></div></div>
    <section className="two-col-grid">
      <Card title="Loan Details / Borrower Info" icon={FileText}><KeyValueGrid data={[['Loan amount','$560,000'],['Loan type','Conventional'],['Borrower','James Miller'],['DTI','32%'],['LTV','70%'],['Term','30 years fixed'],['Credit score','760'],['Reserves','9 months']]}/></Card>
      <Card title="Property Information" icon={Building2}><KeyValueGrid data={[['Property type','Single Family'],['Year built','2018'],['Square footage','2,850 sq ft'],['Lot size','0.21 acres'],['Location','Austin, TX'],['Condition','Excellent']]}/><div className="flat-property-illustration" aria-label="Abstract property illustration"><Building2 size={56}/><span>Property image placeholder</span></div></Card>
      <Card title="Value Comparison / Key Metrics" icon={BarChart3}><BarChartFlat values={[560,538,575]} labels={['Subject','Market Avg','Model Estimate']}/><div className="metric-list"><Metric label="Subject value" value="$560k"/><Metric label="Variance" value="+4.1%"/><Metric label="Confidence" value="92%"/></div></Card>
      <Card title="Agent Info / Relevant Information" icon={BrainCircuit}><div className="agent-list">{['Property Valuation Agent','Risk Analysis Agent','Document Review Agent','Market Intelligence Agent'].map(x=><div key={x}><CheckCircle2 size={17}/><span>{x}</span></div>)}</div><div className="callout"><strong>Agent consensus</strong><span>Strong agreement</span><p>Property value is aligned with market comparables and current risk is acceptable.</p><button className="text-link" onClick={()=>setPage('audit')}>Open AI audit <ChevronRight size={15}/></button></div></Card>
    </section>
  </>
}

function Audit(){
  return <>
    <Hero eyebrow="AI audit" title="AL-AI Audit & Deliberation Console" subtitle="Multi-agent analysis, reasoning, and final recommendation for transparent decisions." compact/>
    <section className="agent-grid">{[
      ['Credit Agent','Agree','Strong credit profile, stable income, low existing obligations.'],
      ['Property Agent','Agree','Property condition and valuation support lending criteria.'],
      ['Market Agent','Consider','Strong demand, but near-term supply warrants monitoring.'],
      ['Risk Agent','Consider','Overall risk within appetite; additional reserves advised.']
    ].map(([name,state,txt])=><Card key={name} title={name} icon={BrainCircuit}><span className={`pill ${state==='Agree'?'low':'medium'}`}>{state}</span><p>{txt}</p><button className="text-link">View full analysis <ChevronRight size={15}/></button></Card>)}</section>
    <section className="two-col-grid">
      <Card title="Agent Consensus" icon={Users}><Donut value={75} label="agreement" segments={[50,25,0,25]}/><div className="legend-list"><span><i className="legend green"/>Agree 2</span><span><i className="legend amber"/>Consider 1</span><span><i className="legend grey"/>No opinion 1</span></div></Card>
      <Card title="AI Recommendation" icon={Sparkles}><div className="recommendation"><CircleCheckBig/><div><span className="eyebrow">Recommendation</span><h3>Approve with Conditions</h3><p>Core lending criteria are met with manageable risk and clear conditions.</p></div></div><div className="mini-stats three"><div><strong>92%</strong><span>Confidence</span></div><div><strong>Moderate</strong><span>Risk rating</span></div><div><strong>3</strong><span>Conditions</span></div></div></Card>
    </section>
    <Card title="Reasoning / Decision Trail" icon={FileText}><Timeline/></Card>
  </>
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
function Metric({label,value}){return <div className="metric"><span>{label}</span><strong>{value}</strong></div>}
function MetricCard({icon:Icon,label,value,delta}){return <Card><div className="metric-card"><span className="icon-chip"><Icon size={19}/></span><span>{label}</span><strong>{value}</strong><small>{delta}</small></div></Card>}
function BarChartFlat({values,labels}){const max=Math.max(...values);return <div className="bar-chart">{values.map((v,i)=><div className="bar-col" key={labels[i]}><strong>{`$${v}k`}</strong><div className="bar" style={{height:`${(v/max)*150}px`}}/><span>{labels[i]}</span></div>)}</div>}
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
function Timeline(){const rows=[['10:12','Credit Agent','Completed borrower and financial analysis.'],['10:15','Property Agent','Validated property details and appraisal.'],['10:18','Market Agent','Reviewed market conditions and supply.'],['10:22','Risk Agent','Identified moderate risk and proposed conditions.'],['10:25','AI Synthesis','Recommended approval with conditions.']]; return <ol className="timeline">{rows.map(([t,a,b])=><li key={t+a}><time>{t}</time><strong>{a}</strong><span>{b}</span></li>)}</ol>}
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
const defaultPreferences={
  name:'Sarah Chen',email:'sarah.chen@example.com',organisation:'Agentic Lender',
  applicationUpdates:true,documentRequests:true,weeklySummary:false,
  density:'comfortable',reduceMotion:false,
};
function loadPreferences(){
  try {
    const saved=JSON.parse(localStorage.getItem(preferencesKey));
    if(!saved||typeof saved!=='object') return {...defaultPreferences};
    const result={...defaultPreferences};
    for(const key of ['name','email','organisation']){
      if(typeof saved[key]==='string'&&saved[key].trim()) result[key]=saved[key].trim().slice(0,key==='email'?254:80);
    }
    for(const key of ['applicationUpdates','documentRequests','weeklySummary','reduceMotion']){
      if(typeof saved[key]==='boolean') result[key]=saved[key];
    }
    if(['comfortable','compact'].includes(saved.density)) result.density=saved.density;
    return result;
  } catch { return {...defaultPreferences}; }
}
function SettingsPage({preferences,onSave}){
  const [draft,setDraft]=useState(()=>({...preferences}));
  const [notice,setNotice]=useState('');
  const [error,setError]=useState('');
  const dirty=Object.keys(defaultPreferences).some(key=>draft[key]!==preferences[key]);
  function change(key,value){setDraft(current=>({...current,[key]:value}));setNotice('');setError('');}
  function save(event){
    event.preventDefault();
    const next={...draft,name:draft.name.trim(),email:draft.email.trim(),organisation:draft.organisation.trim()};
    if(!next.name||!next.organisation){setError('Enter a name and organisation.');return;}
    try {localStorage.setItem(preferencesKey,JSON.stringify(next));}
    catch {setError('Settings could not be saved in this browser. Please try again.');return;}
    onSave(next);setDraft(next);setError('');setNotice('Settings saved in this browser.');
  }
  return <>
    <Hero eyebrow="Sample workspace" title="Settings" subtitle="Your profile, notification preferences, and workspace appearance." compact/>
    <form className="settings-form" onSubmit={save}>
      <section className="settings-section" aria-labelledby="settings-profile-title">
        <div className="settings-section-title"><UserRoundCheck size={21}/><div><h2 id="settings-profile-title">Profile</h2><p>Account and organisation details.</p></div></div>
        <div className="settings-fields">
          <label>Full name<input name="name" autoComplete="name" maxLength={80} required value={draft.name} onChange={e=>change('name',e.target.value)}/></label>
          <label>Email address<input name="email" type="email" autoComplete="email" maxLength={254} required value={draft.email} onChange={e=>change('email',e.target.value)}/></label>
          <label>Organisation<input name="organisation" autoComplete="organization" maxLength={80} required value={draft.organisation} onChange={e=>change('organisation',e.target.value)}/></label>
          <label>Account role<input value="Underwriter" readOnly/></label>
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
