#!/usr/bin/env python3
"""Editable low-fidelity design asset generator; not a game UI. Dependencies: Pillow, fontTools[woff]."""
from pathlib import Path
import argparse,io
from fontTools.ttLib import TTFont
from xml.sax.saxutils import escape
from PIL import ImageFont
import json,re

P=Path(__file__).resolve().parents[3];U=P/'design/ux';W=U/'wireframes'
FONTDIR=P/'design/accessibility/fonts'
cli=argparse.ArgumentParser(description='Regenerate P23 isolated design SVG/catalog/gallery only. No game source writes.')
cli.add_argument('--write',action='store_true',required=True,help='explicitly overwrite P23 generated design files in this package')
cli.parse_args()
assert json.loads((P/'actual_path_request.json').read_text())['production_write_authorized'] is False
font_bytes={}
for language,name in [('zh-Hans','noto-sans-sc-chinese-simplified-400-normal.woff2'),('ja','noto-sans-jp-japanese-400-normal.woff2')]:
 f=TTFont(FONTDIR/name);f.flavor=None;b=io.BytesIO();f.save(b);font_bytes[language]=b.getvalue()
INK='#1b2635';MUTED='#445266';LINE='#626e7d';SURFACE='#f2f4f7';FOCUS='#005fcc';WHITE='#ffffff'
fontcache={}
def font(size,lang='zh-Hans'):
 key=(size,lang)
 if key not in fontcache:fontcache[key]=ImageFont.truetype(io.BytesIO(font_bytes['ja' if lang=='ja' else 'zh-Hans']),size)
 return fontcache[key]
def width(s,size=18,lang='zh-Hans'):return font(size,lang).getlength(s)
def wrap(s,maxw,size=18,lang='zh-Hans'):
 lines=[];line=''
 for c in s:
  if c=='\n':lines.append(line);line='';continue
  if line and width(line+c,size,lang)>maxw:
   if c in '、。，．！？：；）］｝〉》」』】〕)]}!?.,:;':
    # move the previous character as well, avoiding a prohibited line-start.
    if len(line)>1:lines.append(line[:-1]);line=line[-1]+c
    else:lines.append(line+c);line=''
   else:lines.append(line);line=c
  else:line+=c
 if line:lines.append(line)
 return lines

class Board:
 def __init__(self,code,title,screen,states,notes,height=856):
  self.code=code;self.title=title;self.screen=screen;self.states=states;self.notes=notes;self.height=height;self.parts=[];self.texts=[];self.regions=[]
  self.parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="{height}" viewBox="0 0 1280 {height}" role="img" aria-labelledby="title desc" data-wireframe-id="{code}" data-screen-id="{screen}">')
  self.parts.append(f'<title id="title">{escape(title)}</title><desc id="desc">P23 可编辑低保真线框。设计夹具，数字和名称不构成正式玩法参数。{escape(notes)}</desc>')
  self.parts.append('''<defs><style>@font-face{font-family:P23SC;src:url(../../accessibility/fonts/noto-sans-sc-chinese-simplified-400-normal.woff2) format("woff2");font-weight:400}@font-face{font-family:P23JP;src:url(../../accessibility/fonts/noto-sans-jp-japanese-400-normal.woff2) format("woff2");font-weight:400}@font-face{font-family:P23Symbols;src:url(../../accessibility/fonts/DejaVuSans.ttf) format("truetype");font-weight:400}text{font-family:P23SC,P23JP,P23Symbols,sans-serif;font-weight:400}</style><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10Z" fill="#626e7d"/></marker></defs>''')
  self.rect(0,-48,1280,height,fill=WHITE,stroke='none')
  self.rect(0,-48,1280,48,fill=INK,stroke='none')
  self.text(24,-36,f'P23 / {code}   {title}',20,WHITE,maxw=870)
  self.text(960,-34,'低保真设计 · 非正式UI',16,WHITE,maxw=296)
  self.line(0,720,1280,720)
  self.text(24,735,'设计夹具：数字 / 名称仅用于走查；1280×720 为候选逻辑画布，目标屏未冻结。',16,MUTED,maxw=1232)
  self.text(24,766,notes,16,MUTED,maxw=1232)
 def rect(self,x,y,w,h,fill=WHITE,stroke=LINE,sw=1,r=6,dash=None,anchor=None,control=False,tag=None):
  attrs=f' x="{x}" y="{y+48}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"'
  if dash:attrs+=f' stroke-dasharray="{dash}"'
  if anchor:attrs+=f' data-anchor-id="{anchor}"'
  if control:attrs+=' data-control="true"'
  if tag:attrs+=f' data-region="{tag}"'
  self.parts.append('<rect'+attrs+'/>')
  if anchor or control:self.regions.append({'anchor_id':anchor,'control':control,'x':x,'y':y,'width':w,'height':h,'tag':tag})
 def line(self,x1,y1,x2,y2,stroke=LINE,sw=1,dash=None):
  self.parts.append(f'<line x1="{x1}" y1="{y1+48}" x2="{x2}" y2="{y2+48}" stroke="{stroke}" stroke-width="{sw}"'+(f' stroke-dasharray="{dash}"' if dash else '')+'/>')
 def text(self,x,y,s,size=18,fill=INK,maxw=None,lang='zh-Hans',anchor=None,leading=None):
  leading=leading or round(size*1.5,1);ls=wrap(s,maxw,size,lang) if maxw else s.split('\n')
  for i,line in enumerate(ls):
   yy=y+i*leading;ww=width(line,size,lang)
   attrs=f' x="{x}" y="{yy+48}" font-size="{size}" fill="{fill}" dominant-baseline="hanging" lang="{lang}"'
   if lang=='ja':attrs+=' style="font-family:P23JP,P23SC,P23Symbols,sans-serif"'
   if anchor and i==0:attrs+=f' data-anchor-id="{anchor}"'
   self.parts.append('<text'+attrs+'>'+escape(line)+'</text>')
   self.texts.append({'text':line,'x':x,'y':yy,'font_size':size,'measured_width':round(ww,2),'max_width':maxw,'lang':lang,'anchor_id':anchor if i==0 else None})
  return len(ls)*leading
 def button(self,x,y,w,label,aid=None,primary=False,disabled=False,focus=False,size=18,h=48):
  self.rect(x,y,w,h,fill=SURFACE if disabled else INK if primary else WHITE,stroke=INK,sw=2 if primary else 1,dash='5 4' if disabled else None,anchor=aid,control=True)
  tx=x+max(12,(w-width(label,size))/2)
  self.text(tx,y+(h-size*1.25)/2,label,size,WHITE if primary and not disabled else INK,maxw=w-24)
  if focus:self.rect(x-5,y-5,w+10,h+10,fill='none',stroke=FOCUS,sw=3,r=9,tag='focus_indicator')
 def pill(self,x,y,label,w=None,fill=SURFACE,size=16):
  w=w or width(label,size)+24;self.rect(x,y,w,32,fill=fill,r=3);self.text(x+12,y+6,label,size)
 def panel(self,x,y,w,h,title=None,anchor=None):
  self.rect(x,y,w,h,anchor=anchor)
  if title:self.text(x+18,y+16,title,22,maxw=w-36)
 def banner(self,label,sub=None,aid=None,y=72,h=48):
  self.rect(24,y,1232,h,fill=SURFACE,stroke=INK,sw=2,anchor=aid)
  self.text(40,y+12,label,20,maxw=1200)
  if sub:self.text(40,y+44,sub,18,maxw=1200)
 def done(self):
  self.parts.append('</svg>');(W/(self.code+'.svg')).write_text('\n'.join(self.parts)+'\n',encoding='utf-8')
  return {'wireframe_id':self.code,'title':self.title,'screen_id':self.screen,'state_ids':self.states,'svg_relative_path':str((W/(self.code+'.svg')).relative_to(P)),'png_relative_path':str((W/(self.code+'.png')).relative_to(P)),'board_size':[1280,self.height],'screen_rect':[0,48,1280,720],'kind':'EDITABLE_LOW_FIDELITY_DESIGN','runtime_binding':'DESIGN_FIXTURE_ONLY','notes':self.notes,'text_boxes':self.texts,'interactive_regions':self.regions}

boards=[]
def battle(code,title,mode='ready'):
 states={'ready':['B_READY'],'target':['B_CARD_SELECTED','B_TARGET_COMPLETE'],'unknown':['B_UNKNOWN'],'intent_missing':['B_INTENT_MISSING','B_CARD_CONTEXT_MISSING'],'terminal':['B_WIN'],'end':['B_END_REVIEW']}[mode]
 b=Board(code,title,'battle',states,'P14 管终态；P19 管输入与文字；P29 仅管表现。示例预告不等于实际掉血。')
 b.text(24,18,'卡牌战斗',28,anchor='ux.battle.heading');b.text(302,24,'第 2 回合 · 你的回合' if mode!='terminal' else '战斗已结束',22)
 b.text(870,24,'可用费用 2',24,anchor='ux.battle.energy');b.button(1086,14,170,'动态效果：关闭','ux.battle.motion',h=48)
 msg={'ready':'先选卡牌 → 选目标 → 确认出牌','target':'已选：试验·锋刃　目标：演练敌方　费用：1　尚未提交','unknown':'[待确认] 本次出牌结果未知；请查询原操作，新的出牌已暂停。','intent_missing':'[信息未齐] 卡牌 / 意图尚未同步；生命与费用仍显示已确认状态。','terminal':'[战斗胜利] 结果已确认；奖励处理状态需在结算页另行核对。','end':'[确认结束] 当前选择尚未出牌。结束回合后进入敌方行动。'}[mode]
 b.banner(msg,aid='ux.battle.status')
 # Party. Unit cards are semantic placeholders, not portrait assets.
 for i,(name,hp,shield) in enumerate([('锋刃位 A','10 / 10',3),('守护位 B','10 / 10',0),('治愈位 C','10 / 10',0)]):
  y=138+i*68;b.rect(24,y,242,60,fill=WHITE,anchor='ux.battle.party.{unit_key}',control=True)
  b.text(38,y+6,name,20);b.text(38,y+33,'生命 '+hp.replace(' ','')+' 护盾 '+str(shield),20,maxw=214)
 # Enemy card.
 b.panel(286,138,350,196,anchor='ux.battle.enemy.{unit_key}')
 b.rect(306,154,78,92,fill=SURFACE,dash='4 3');b.text(318,176,'敌方\n卡面位',18,maxw=56)
 b.text(404,156,'演练敌方',24);b.text(404,196,'生命 '+('0 / 18' if mode=='terminal' else '12 / 18'),20,anchor='ux.battle.hp.{unit_key}')
 b.text(404,228,'护盾 0',20);b.rect(306,264,310,12,fill=SURFACE,r=0)
 if mode!='terminal':b.rect(306,264,round(310*12/18,2),12,fill=INK,stroke='none',r=0)
 b.text(306,283,'已倒下' if mode=='terminal' else '[已选目标]' if mode=='target' else '目标详情可读；无须悬停',18,maxw=306)
 if mode=='target':b.rect(281,133,360,206,fill='none',stroke=INK,sw=2,tag='selection_indicator')
 b.panel(656,138,600,196,'下一次行动',anchor='ux.battle.intent.{unit_key}')
 if mode=='intent_missing':
  b.text(674,184,'意图尚未同步',26);b.text(674,229,'下一步行动未知；不显示上回合预告。',20,maxw=560);b.text(674,272,'仍按已有出牌 / 回合资格决定可操作性。',18,maxw=560)
 elif mode=='terminal':
  b.text(674,188,'本场战斗已结束',26);b.text(674,240,'不再显示下一次攻击，也不自行切换 Boss 阶段。',18,maxw=552)
 else:
  b.text(674,183,'攻击前排　基础 1 × 1 次',24);b.text(674,224,'目标：锋刃位 A',20);b.text(674,259,'[候选预告] 尚未由核心确认。',18);b.text(674,291,'基础值不是实际掉血；护盾与效果以结算为准。',18,maxw=562)
 b.rect(24,350,1232,62,fill=SURFACE,anchor='ux.battle.log')
 b.text(40,363,'最近结算',18);b.text(190,363,'锋刃位 A：生命减少 0；护盾吸收 1。',20,maxw=1010)
 b.text(190,390,'这条文字来自已提交事件；关闭演出后仍然保留。',16,maxw=1010)
 b.text(24,427,'手牌（示例 5 张；不代表手牌上限）',18);b.text(890,427,'抽牌堆 4　弃牌堆 1　移除 0',16)
 cards=[('试验·锋刃',1,'攻击','基础伤害 4','锋刃位 A'),('试验·防护',1,'防御','护盾 4','守护位 B'),('试验·治疗',1,'治疗','恢复生命 3','治愈位 C'),('试验·增益',1,'增益','效果说明需完整可读','治愈位 C'),('试验·重击',3,'攻击','费用不足；查看详情','锋刃位 A')]
 for i,(name,cost,cat,desc,owner) in enumerate(cards):
  x=24+i*249;y=458;disabled=i==4 or mode in ['unknown','intent_missing','terminal']
  b.rect(x,y,236,174,fill=SURFACE if disabled else WHITE,sw=2 if i==0 and mode=='target' else 1,dash='5 4' if disabled else None,anchor='ux.battle.hand.{card_key}',control=True)
  b.text(x+14,y+14,name,20,maxw=178);b.text(x+190,y+14,str(cost),24)
  b.text(x+14,y+49,'['+cat+'] '+desc,20,maxw=208)
  b.text(x+14,y+116,'归属：'+owner,16,maxw=208)
  b.text(x+14,y+145,'[已选择]' if i==0 and mode=='target' else '详情可读' if disabled else '选择卡牌',16)
 if mode=='unknown':
  b.button(24,644,226,'查询本次操作','ux.battle.command.lookup',primary=True,focus=True)
  b.button(266,644,176,'刷新状态','ux.battle.command.refresh');b.text(474,658,'保留原请求；查询不会创建第二次出牌。',18,maxw=770)
 elif mode=='end':
  b.button(24,644,184,'继续选择','ux.battle.end_cancel',focus=True);b.text(232,658,'确认前仍可查看敌方意图。',18,maxw=560);b.button(1020,644,236,'确认结束回合','ux.battle.end_confirm',primary=True)
 elif mode=='terminal':
  b.text(24,650,'胜利 ≠ 奖励已入账',22,anchor='ux.battle.outcome');b.button(1020,644,236,'查看结算状态','ux.battle.result_route',primary=True)
 else:
  b.button(24,644,180,'查看完整记录','ux.battle.log_open');b.button(220,644,180,'卡牌 / 目标详情','ux.battle.card_details')
  b.button(772,644,142,'取消选择','ux.battle.command.cancel',disabled=mode!='target')
  b.button(930,644,154,'确认出牌','ux.battle.command.play',primary=True,disabled=mode!='target',focus=mode=='target')
  b.button(1100,644,156,'结束回合','ux.battle.command.end_turn')
 return b

for code,title,mode in [('W01_Battle_Ready','战斗 / 可操作态','ready'),('W02_Battle_Target','战斗 / 目标确认','target'),('W03_Battle_Unknown','战斗 / 原操作待确认','unknown'),('W04_Battle_Intent_Missing','战斗 / 意图与卡牌待同步','intent_missing'),('W05_Battle_Result','战斗 / 权威终局','terminal'),('W06_Battle_End_Review','战斗 / 结束回合确认提案','end')]:boards.append(battle(code,title,mode).done())

nav=[('home','旅团营地'),('characters','角色档案'),('party','三人编队'),('growth','角色养成'),('chapters','章节远征'),('settlement','战后结算'),('learning','学习状态')]
def meta(code,title,screen,states,note):
 b=Board(code,title,screen,states,note)
 b.rect(0,0,220,720,fill=SURFACE,stroke='none',r=0);b.line(220,0,220,720)
 b.text(24,24,'言灵旅团',28);b.text(24,66,'导航与内容分区',16,MUTED)
 for i,(sid,label) in enumerate(nav):
  b.button(24,116+i*62,172,label,'ux.nav.'+sid,primary=sid==screen,h=48)
 b.text(24,586,('[连接可用]' if screen=='learning' else '[未连接]')+'\nAnki 状态单独显示',16,MUTED,maxw=172)
 b.text(248,26,dict(nav).get(screen,title),28,anchor='ux.'+screen+'.heading' if screen in dict(nav) else None)
 b.text(908,24,'可用资源 15（示例）',20,anchor='ux.meta.wallet');b.text(908,56,'预留 0 · 取自当前视图',16,MUTED)
 return b

b=meta('W07_Camp','营地 / 主路径','home',['M_READY','L_DISCONNECTED'],'沿用 P20 已有导航；Anki 断连不自动封锁已可用的游戏操作。')
b.rect(248,100,1008,52,fill=SURFACE,anchor='ux.meta.save_status');b.text(266,114,'存档可操作　｜　学习连接：未连接　｜　当前视图已确认',20)
b.panel(248,174,1008,210,'准备下一次出发')
b.text(268,220,'先确认已保存编队，再选择关卡。',22);b.text(268,261,'角色立绘区域由美术岗位提供；本线框只标记空间与信息。',18,MUTED,maxw=950)
b.button(268,312,220,'整理三人编队','ux.home.party_cta',primary=True);b.button(508,312,200,'查看章节','ux.home.chapters_cta')
b.text(248,410,'当前已保存编队',22)
for i,(name,role) in enumerate([('璃火','攻击'),('千澄','守护'),('羽铃','支援')]):
 x=248+i*342;b.panel(x,450,324,94);b.text(x+18,467,f'{i+1:02d}  {name}',22);b.text(x+18,505,role+' · 等级 1（示例）',18)
b.panel(248,568,488,126,'学习记录');b.text(266,612,'尚未取得可核验的学习记录。',18,maxw=450);b.button(266,644,214,'查看学习状态','ux.home.learning_cta',h=44)
b.panel(754,568,502,126,'章节记录');b.text(772,612,'挑战进度与首通资格分别读取。',18,maxw=460);b.button(772,644,214,'打开章节','ux.home.chapter_summary_cta',h=44)
boards.append(b.done())

b=meta('W08_Party_Draft','编队 / 草稿与已保存','party',['P_DIRTY','P_INVALID','P_SAVED'],'选择已占用角色时只交换草稿席位；保存成功须由新的已提交视图证明。')
b.rect(248,100,1008,80,fill=SURFACE,anchor='ux.party.draft_status');b.text(266,117,'[尚未保存] 当前排列只保留在此页。',22);b.text(266,150,'页面选择属于草稿；提交成功后才显示“编队已保存”。',18)
for i,(name,role) in enumerate([('羽铃','支援'),('千澄','守护'),('璃火','攻击')]):
 x=248+i*342;b.panel(x,206,324,334,f'席位 {i+1:02d}')
 b.rect(x+18,258,288,118,fill=SURFACE,dash='5 4');b.text(x+76,294,'角色立绘区域',22)
 b.button(x+18,396,288,f'{name} · {role}  ▾','ux.party.slot.{slot}',focus=i==0)
 b.text(x+18,466,'等级 1 · 属性来自角色视图',18,maxw=288);b.text(x+18,504,'当前草稿选择',16,MUTED)
b.text(248,566,'已保存顺序：璃火 → 千澄 → 羽铃',20)
b.button(248,626,240,'恢复已保存编队','ux.party.restore');b.button(1016,626,240,'保存三人编队','ux.party.save',primary=True)
boards.append(b.done())

b=meta('W09_Growth_Confirm','养成 / 消耗确认','growth',['G_CONFIRM'],'这是 P20 已有升级确认框的焦点规范：默认取消；一次确认只提交一个原请求。')
b.panel(248,100,1008,174,'璃火 · 当前等级 1');b.text(266,152,'生命 96　攻击 17　防御 5　支援 3',20,anchor='ux.growth.attributes');b.text(266,206,'升级费用与资格来自 P17；不由界面重新计算。',18)
b.rect(370,302,744,326,fill=WHITE,stroke=INK,sw=3,anchor='ux.growth.dialog')
b.text(398,326,'确认升级',28);b.text(398,374,'角色：璃火　　等级：1 → 2',22)
b.text(398,416,'本次消耗：训练代币 4（示例）',22,anchor='ux.growth.cost');b.text(398,456,'提交后读取新的等级与钱包；等待中不重复提交。',18,maxw=688)
b.button(398,548,220,'暂不升级','ux.growth.dialog_cancel',focus=True);b.button(846,548,240,'确认升级并提交','ux.growth.dialog_confirm',primary=True)
b.text(248,660,'键盘：Tab 在框内切换；Esc 关闭并回到触发按钮。',18,maxw=980)
boards.append(b.done())

b=meta('W10_Learning_Quarantine','学习 / 隔离与到账分离','learning',['L_QUARANTINED','L_APPLIED_UNPROVEN'],'连接、账本状态、钱包证明是三条独立信息；查询只读，不包含强制入账按钮。')
b.panel(248,100,1008,100,'[待核对 · 已隔离]',anchor='ux.learning.record');b.text(266,149,'这条记录尚未计入可用奖励。你无需改变 Anki 评分。',20,maxw=950)
for x,w,title,body,aid in [(248,324,'连接','Anki 连接可用','ux.learning.connection'),(590,324,'记录','待核对 · 已隔离','ux.learning.reason'),(932,324,'钱包','15（最近确认示例）','ux.learning.wallet_proof')]:
 b.panel(x,224,w,134,title,anchor=aid);b.text(x+18,278,body,20,maxw=w-36);b.text(x+18,321,'本条尚未授奖' if title=='记录' else '连接不代表入账' if title=='连接' else '未计入隔离记录',16,MUTED,maxw=w-36)
b.panel(248,382,1008,142,'接下来可以做什么');b.text(266,430,'重新查询此记录的处理状态；保持正常复习即可。',20,maxw=950);b.text(266,471,'技术编号、原始原因码与证明来源放在可展开的记录详情中。',18,maxw=950)
b.button(248,552,224,'重新查询状态','ux.learning.refresh',primary=True,focus=True);b.button(490,552,224,'查看记录详情','ux.learning.details')
b.text(248,628,'状态更新后保留当前焦点，只读出有变化的一条摘要。',18,maxw=1000)
boards.append(b.done())

b=meta('W11_Growth_Pending','养成 / 重启后仍待确认','growth',['M_UNKNOWN','M_RESTART_PENDING'],'P21 的隔离查询能力已交付；P20 ↔ P21 正式网关未受理，不可凭新空存档解除未决。')
b.rect(248,100,1008,146,fill=SURFACE,stroke=INK,sw=2,anchor='ux.meta.pending')
b.text(266,117,'[上次操作结果待确认]',24);b.text(266,159,'先查询原操作。刷新、返回或重启都不会发起第二次升级。',20,maxw=950)
b.button(266,192,220,'查询原操作','ux.meta.lookup',primary=True,focus=True)
b.panel(248,270,1008,266,'璃火 · 最近已确认状态');b.text(266,322,'等级 1　生命 96　攻击 17　防御 5',22)
b.text(266,371,'下次等级与消耗预览仍可阅读，暂时不能再次提交。',20,maxw=950)
b.button(266,440,220,'确认升级','ux.growth.upgrade',disabled=True);b.text(514,452,'不可用原因：请先核对上次操作结果。',18,maxw=680)
b.panel(248,560,1008,132,'可继续浏览');b.text(266,607,'页面导航不会清除原请求。技术编号保留在详情中，不代替说明文案。',18,maxw=950)
boards.append(b.done())

b=meta('W12_Chapters','章节 / 挑战与首通资格','chapters',['C_LOCKED','M_SAVE_RECOVERY_REQUIRED'],'关卡状态按 P18 原视图显示；恢复冻结时入口禁用原因覆盖“可挑战”，但不改首通事实。')
b.rect(248,100,1008,76,fill=SURFACE,anchor='ux.meta.save_status');b.text(266,114,'[存档需要核对] 可继续浏览，新的出战、消耗与领取已暂停。',20,maxw=950)
for i,(title,challenge,first) in enumerate([('01 · 游离字屑','已通关','首通资格：已使用'),('02 · 失序校勘者','已解锁','首通资格：尚未使用')]):
 y=202+i*222;b.panel(248,y,1008,194,title,anchor='ux.chapters.stage.{stage_key}')
 b.text(266,y+58,challenge+'　｜　'+first,20,anchor='ux.chapters.eligibility.{stage_key}')
 b.text(266,y+100,'奖励预览仅供阅读；是否可领取以处理状态为准。',18,maxw=660)
 b.button(1010,y+22,226,'查看关卡','ux.chapters.stage.{stage_key}');b.button(1010,y+88,226,'准备出发','ux.chapters.enter.{stage_key}',disabled=True)
 b.text(1010,y+145,'存档待核对，暂停出战',16,maxw=226)
b.text(248,662,'不可用原因要留在按钮附近；不要同时显示 READY 与“暂停出战”。',18,maxw=1008)
boards.append(b.done())

b=meta('W13_Settlement_Pending','结算 / 胜利与奖励未知','settlement',['R_UNKNOWN','R_REVIEW'],'只接受 P14 权威战斗结果与 P18 处理状态；胜利、已消耗首通资格、已入账不能互相推导。')
b.panel(248,100,1008,154,'[战斗胜利]',anchor='ux.settlement.battle_result');b.text(266,158,'本场结果已确认；不代表奖励已经入账。',22,maxw=950)
b.rect(248,282,1008,170,fill=SURFACE,stroke=INK,sw=2,anchor='ux.settlement.reward_status');b.text(266,303,'[奖励结果待确认]',26);b.text(266,351,'请查询本次领取结果。返回章节后仍保留原操作记录。',20,maxw=950);b.text(266,401,'首通资格：以关卡当前记录为准；界面不再次计算或发放。',18,maxw=950)
b.button(248,486,250,'查询领取结果','ux.settlement.lookup',primary=True,focus=True);b.button(520,486,220,'返回章节','ux.settlement.return')
b.panel(248,572,1008,120,'原记录详情');b.text(266,619,'战斗编号、原请求编号、来源与处理原因可展开查看；主提示保持自然语言。',18,maxw=950)
boards.append(b.done())

b=meta('W14_Characters','角色 / 档案入口','characters',['M_READY'],'角色总数未冻结；三席编队不等于只有三名角色。此处三项仅复用上游示例。')
b.text(248,108,'查看同伴的当前信息，再进入养成。',22,maxw=980)
for i,(name,role) in enumerate([('璃火','攻击'),('千澄','守护'),('羽铃','支援')]):
 x=248+i*342;b.panel(x,166,324,442)
 b.rect(x+18,184,288,180,fill=SURFACE,dash='5 4');b.text(x+76,250,'可编辑立绘区',22)
 b.text(x+18,394,name+' · '+role,24);b.text(x+18,439,'等级 1（当前已确认）',18)
 b.button(x+18,522,288,'查看养成','ux.characters.item.{character_key}',primary=i==0)
b.text(248,654,'长名称保留详情入口；不得靠缩小到不可读来塞入卡面。',18,maxw=1008)
boards.append(b.done())

b=meta('W15_Handoff','出战 / 已有战斗交接','handoff',['C_ACTIVE'],'此态已存在于 P20；进入 P19 的真实路由等待 P13/P19/P20 受理，不在本岗接线。')
b.panel(248,100,1008,226,'已有一场战斗待继续',anchor='ux.handoff.active_battle')
b.text(266,166,'关卡与队伍采用出战时已提交的引用。',22,maxw=950);b.text(266,218,'暂时无法接入战斗界面；请查询已创建战斗的状态。',20,maxw=950)
b.button(266,354,250,'查询出战状态','ux.handoff.refresh',primary=True,focus=True);b.button(540,354,200,'返回章节','ux.handoff.return')
b.rect(248,450,1008,148,fill=SURFACE);b.text(266,470,'返回页面不会关闭这场战斗，也不会自动再创建一场。',22,maxw=950);b.text(266,524,'正式接线后可进入已存在的 battle 引用，不能由 UI 生成胜负或奖励。',18,maxw=950)
boards.append(b.done())

# Typography board is a specification plate, not a new application screen.
b=Board('W16_Typography','中日排版 / 缺字与长文样张','battle',['B_INTENT_CANDIDATE','L_QUARANTINED'],'此页是排版审查板，不是新增产品页面；日本语文案待双语人工审核。')
b.panel(24,24,600,218,'中文关键提示 · 20px')
b.text(44,78,'下一次行动：攻击前排；基础 12 × 2 次。\n实际掉血以结算为准。',20,maxw=558,leading=32)
b.text(44,169,'关键数值、否定词与目标不使用省略号。',18,maxw=558)
b.panel(648,24,608,218,'日本語 · 20px')
b.text(668,78,'次の行動：前列を攻撃。基礎値 12 × 2 回。\n実際の減少量は確定した結果を参照。',20,maxw=568,lang='ja',leading=32)
b.text(668,169,'「確認しました」。対象（前列）を確認。',18,maxw=568,lang='ja')
b.panel(24,268,1232,166,'长名称与注音')
b.text(44,324,'星のあいだに置き忘れた観測記録と三度目の校閲',22,maxw=1190,lang='ja')
b.text(44,375,'語彙（ごい） ／ 取り消す（とりけす）　　HP 128 / 160　　護盾 +8',20,maxw=1190,lang='ja')
b.panel(24,460,1232,224,'缺字：明确替代，原文可查')
b.text(44,516,'[缺字 U+20BB7] 野的记录　　[缺字 U+F0000]',22,maxw=1190)
b.text(44,564,'本轮字体不包含这两个测试码位；保留原始 UTF-8 供详情查看，不擅自改成“吉”。',20,maxw=1190)
b.text(44,621,'界面按语言切换字形；事件 ID、原始 Anki 文本和哈希不随显示层规范化。',18,maxw=1190)
boards.append(b.done())

b=Board('W17_Battle_Large_Text','战斗 / 大字滚动布局提案','battle',['B_READY'],'本页示意 200% 文字重排，不是目标引擎缩放实测；一次展示较少卡片，完整内容可滚动。')
b.text(24,18,'卡牌战斗',40,anchor='ux.battle.heading');b.text(480,24,'第 2 回合',32);b.text(930,24,'费用 2',40,anchor='ux.battle.energy')
b.rect(24,94,1232,318,fill=SURFACE,anchor='ux.battle.intent.{unit_key}')
b.text(48,116,'下一次行动',40);b.text(48,178,'攻击前排 · 基础 1 × 1 次',40,maxw=1184)
b.text(48,240,'目标：锋刃位 A',40,maxw=1184)
b.text(48,310,'候选预告；基础值不是实际掉血。',32,maxw=1184)
b.rect(24,436,1232,154,anchor='ux.battle.hand.{card_key}',control=True)
b.text(48,458,'试验·锋刃　费用 1',40,maxw=1184);b.text(48,524,'攻击 · 基础伤害 4　　向下滚动查看其他手牌',32,maxw=1184)
b.button(24,622,320,'查看完整记录','ux.battle.log_open',size=28,h=72);b.button(744,622,244,'确认出牌','ux.battle.command.play',disabled=True,size=28,h=72);b.button(1012,622,244,'结束回合','ux.battle.command.end_turn',size=28,h=72)
boards.append(b.done())

b=Board('W00_Information_Architecture','主路径 / 信息架构','home',['M_READY'],'虚线为尚未接线的跨模块路径；回查学习与导航不产生奖励；无新常驻页面。')
nodes={'learning':(24,40,'学习状态','连接 / 记录 / 钱包证明'),'home':(476,40,'旅团营地','已保存编队 / 当前资源'),'characters':(928,40,'角色档案','角色事实 / 查看养成'),'party':(24,270,'三人编队','草稿 ≠ 已提交'),'chapters':(476,270,'章节远征','挑战 / 首通 / 待核对'),'growth':(928,270,'角色养成','资格 / 消耗 / 原请求'),'handoff':(24,500,'出战交接','已有战斗引用'),'battle':(476,500,'卡牌战斗','出牌 / 意图 / 权威结果'),'settlement':(928,500,'战后结算','战斗结果 ≠ 奖励结果')}
def arrow(x1,y1,x2,y2,dash=False):b.parts.append(f'<path d="M{x1} {y1+48} L{x2} {y2+48}" fill="none" stroke="{LINE}" stroke-width="2" marker-end="url(#arrow)"'+(' stroke-dasharray="6 5"' if dash else '')+'/>')
arrow(476,104,308,104);arrow(760,104,928,104);arrow(1070,170,1070,270);arrow(610,170,166,270);arrow(308,334,476,334);arrow(928,334,760,334);arrow(610,400,166,500);arrow(308,564,476,564,True);arrow(760,564,928,564,True);arrow(1070,500,760,400)
for sid,(x,y,title,sub) in nodes.items():
 b.rect(x,y,284,130,fill=SURFACE,stroke=INK,sw=2,dash='5 4' if sid=='handoff' else None);b.text(x+18,y+18,title,26,maxw=248);b.text(x+18,y+66,sub,18,maxw=248);b.text(x+18,y+101,('P19 / S03' if sid=='battle' else 'P20 / 既有页面'),16,MUTED)
b.text(24,664,'主循环：检查状态 → 培养 / 编队 → 章节 → 战斗 → 结算；学习异常始终可独立查看。',18,maxw=1232)
boards.append(b.done())

boards.sort(key=lambda x:x['wireframe_id'])
(U/'wireframe_catalog.json').write_text(json.dumps({'version':'P23-WIREFRAMES/0.1.0-proposal','items':boards},ensure_ascii=False,indent=2)+'\n')
# Review file embeds vector plates so text remains searchable; no game logic or network calls.
head='''<!doctype html><html lang="zh-Hans"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>P23 线框审查册</title><style>@font-face{font-family:P23SC;src:url(../accessibility/fonts/noto-sans-sc-chinese-simplified-400-normal.woff2)}@font-face{font-family:P23JP;src:url(../accessibility/fonts/noto-sans-jp-japanese-400-normal.woff2)}*{box-sizing:border-box}body{margin:0;padding:24px;background:#e9edf2;color:#1b2635;font:18px/1.6 P23SC,P23JP,sans-serif}header,nav,section{max-width:1280px;margin:0 auto 24px}h1{font-size:32px}h2{font-size:24px}p{max-width:80ch}nav{display:flex;flex-wrap:wrap;gap:12px}a{color:#124683;display:inline-block;min-height:44px;padding:9px 14px;background:white;border:1px solid #626e7d;border-radius:4px;text-decoration:underline}a:focus-visible{outline:3px solid #005fcc;outline-offset:3px}.plate{background:#fff;overflow:auto}svg{display:block;width:1280px;max-width:none}details{padding:16px;background:white;margin:10px 0}summary{cursor:pointer;min-height:44px}code{overflow-wrap:anywhere}@media print{body{padding:0;background:white}header,nav,.notes{display:none}section{break-after:page;page-break-after:always;margin:0}section>h2{display:none}.plate{overflow:visible}svg{width:100%;height:auto}a{border:0}}</style><header><h1>言灵旅团 · P23 线框审查册</h1><p>本文件是可搜索、可编辑 SVG 线框的离线阅读入口。图中数值与人物名均为走查夹具；不连接 Anki、钱包、战斗核心或存档。</p><p>优先看 W01–W06 战斗逐态；再看 W08–W13 的草稿、消耗与异常。方向键 / 手柄操作规则在 keyboard_focus_matrix.tsv；本册不模拟这些产品行为。</p></header><nav aria-label="线框目录">'''
body=[head]
for row in boards:body.append(f'<a href="#{row["wireframe_id"]}">{row["wireframe_id"].split("_")[0]} {escape(row["title"])}</a>')
body.append('</nav><main>')
for row in boards:
 svg=(P/row['svg_relative_path']).read_text();svg=re.sub(r'<style>.*?</style>','',svg,flags=re.S)
 # Scope internal SVG title/desc/marker IDs to avoid duplicate document IDs.
 code=row['wireframe_id'];svg=svg.replace('id="title"',f'id="{code}-title"').replace('id="desc"',f'id="{code}-desc"').replace('aria-labelledby="title desc"',f'aria-labelledby="{code}-title {code}-desc"').replace('id="arrow"',f'id="{code}-arrow"').replace('url(#arrow)',f'url(#{code}-arrow)')
 body.append(f'<section id="{code}" aria-labelledby="{code}-heading"><h2 id="{code}-heading">{escape(row["title"])}</h2><div class="plate">{svg}</div><p class="notes">状态：{escape(", ".join(row["state_ids"]))}。 <a href="wireframes/{code}.svg">打开可编辑 SVG</a> <a href="#top">回到目录</a></p></section>')
body.append('</main></html>');body[0]=body[0].replace('<header>','<header id="top">')
(U/'P23_wireframe_review.html').write_text('\n'.join(body),encoding='utf-8')
print(json.dumps({'wireframes':len(boards),'svg_texts':sum(len(b['text_boxes']) for b in boards),'interactive_regions':sum(len(b['interactive_regions']) for b in boards)},ensure_ascii=False))
