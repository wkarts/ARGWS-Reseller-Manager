'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const params = $('params'), selector = $('connections'), actions = $('actions');
  const out = $('output'), message = $('message');
  const token = sessionStorage.getItem('reseller_token') || '';
  const labels = {
    list_clients:'Listar clientes', get_client:'Consultar cliente',list_plans:'Consultar planos',
    list_technologies:'Consultar tecnologias',get_balance:'Consultar saldo',list_resellers:'Consultar revendedores',
    get_reseller:'Consultar revendedor',list_payments:'Consultar pagamentos',create_client:'Cadastrar cliente',
    renew_client:'Renovar cliente',change_plan:'Alterar plano',change_screens:'Alterar telas',
    migrate_technology:'Migrar tecnologia',enable_client:'Ativar cliente',disable_client:'Bloquear cliente',
    delete_client:'Excluir cliente',create_reseller:'Criar sub-revendedor',update_reseller:'Alterar revendedor',
    credit_transfer:'Transferir créditos',create_payment:'Criar cobrança'
  };
  const routes = [
    ['Clientes IPTV — listagem','/clients/'],
    ['Cadastrar cliente IPTV','/clients/create/'],
    ['Clientes P2P — listagem','/p2p/'],
    ['Cadastro P2P','/p2p/create/'],
    ['Revendedores — listagem','/resellers/'],
    ['Cadastrar revendedor','/resellers/create/'],
    ['Revendedores bloqueados por recarga','/resellers/no_recharge/'],
    ['Conexões ativas','/connections/'],
    ['Logs de créditos','/logs/credits/'],
    ['Logs de vendas','/logs/sales/'],
    ['Logs de clientes','/logs/clients/'],
    ['Logs de revendedores','/logs/resellers/']
  ];
  const list = $('observed');
  for (const [name,path] of routes) {
    const node=document.createElement('div');node.className='item';
    const label=document.createElement('strong');label.textContent=name;
    const code=document.createElement('code');code.textContent=path;
    node.append(label,code);list.append(node);
  }
  const allActions=Object.keys(labels).sort();
  for(const name of allActions) {
    const option=document.createElement('option');option.value=name;option.textContent=labels[name];
    actions.append(option);
  }
  actions.value='list_clients';
  async function call(path,options={}) {
    if(!token) throw new Error('Entre primeiro no painel principal do Reseller Manager.');
    const res=await fetch(path,{
      ...options, headers:{'Authorization':'Bearer '+token,'Accept':'application/json',
        ...(options.body?{'Content-Type':'application/json'}:{})}
    });
    const data=await res.json().catch(()=>({error:{message:'Resposta local inválida.'}}));
    if(!res.ok) throw new Error(data.error?.message||('HTTP '+res.status));
    return data;
  }
  async function load(){
    try {
      const connections=await call('/api/v1/connections');
      selector.replaceChildren();
      if(!connections.length) throw new Error('Nenhuma conexão cadastrada na instalação.');
      for(const item of connections){
        const option=document.createElement('option');option.value=item.id;option.textContent=item.name;
        selector.append(option);
      }
      message.textContent='';
    } catch(e) {
      message.textContent=e.message;
      selector.replaceChildren();
      const option=document.createElement('option');option.textContent='Nenhuma conexão disponível';selector.append(option);
    }
  }
  async function execute(all=false){
    message.textContent='';
    if(!selector.value){message.textContent='Selecione uma conexão.';return;}
    let input={};
    if(!all){
      try {
        input=JSON.parse(params.value.trim()||'{}');
        if(!input || Array.isArray(input) || typeof input!=='object')
          throw new Error('Informe um objeto JSON.');
      }catch(e){message.textContent='Parâmetros inválidos: '+e.message;return;}
    }
    const btns=[$('simulate'),$('matrix')];btns.forEach(x=>x.disabled=true);
    try {
      const base='/api/v1/connections/'+encodeURIComponent(selector.value)+'/dry-run';
      const data=all?await call(base):await call(base+'/'+encodeURIComponent(actions.value),{
        method:'POST',body:JSON.stringify({parameters:input})
      });
      out.textContent=JSON.stringify(data,null,2);
    }catch(e){message.textContent=e.message;}
    finally{btns.forEach(x=>x.disabled=false);}
  }
  $('simulate').addEventListener('click',()=>execute(false));
  $('matrix').addEventListener('click',()=>execute(true));
  load();
})();
