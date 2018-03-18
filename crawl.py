# -*- coding: utf-8 -*-
"""
Created on Fri Mar 16 11:04:20 2018

爬取 https://weibo.cn/  中指定话题的微博，采用了微博的高级搜索

@author: wansho
"""

from urllib.request import urlopen
from urllib.request import Request
from urllib.parse import quote

from bs4 import BeautifulSoup

import my_io
import re

import microblog

# 用于延时
import time

# 用于生成延时随机数
import random

import sys

'''
设置要爬取的url

mobile高级搜索设置

返回要爬取的url
'''
def set_url(ori,keyword, start_time, end_time, sort, smblog, others):
    
    connector = '&'
 
    url = ori +  connector + keyword + connector + start_time \
        + connector + end_time + connector + sort \
        + connector + url_smblog + connector + others
        
    
    return url

############################################################### 

'''
下载给定url的网页

返回值：网页的 字符串 形式
如果返回 -1，说明爬取失败， 那么马上 进行数据的存储

'''
def downloadHtml(url):

    # 模拟了真实的浏览器，包括 cookie,user-agent等元素，最好是在进入了某一个电影的评论页面，再获取header
    headers = { 
		'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
		 
		'Accept-Language':'zh-CN,zh;q=0.9',
		 'Cache-Control':'max-age=0',
		'Connection':'keep-alive',
		'Cookie':'WEIBOCN_WM=3333_2001; ALF=1523686076; SCF=AnA5vjYoP5UxdBHxe5-hFYridMNAWw5uGpGR_ES8HicM__1dKu5Fo_2k1Z1gI8INK4H-wP4i9XlQqFtnZFqb_1Y.; SUB=_2A253rmOdDeRhGeBO4lMU-S3Nzj6IHXVVUQ3VrDV6PUJbktAKLXjFkW1NRYuzLZXesXLlghQGPXJ5JlZVP9wWWeMD; SUBP=0033WrSXqPxfM725Ws9jqgMF55529P9D9Wh224JmmGS16QC9q88gApDH5JpX5K-hUgL.Foq71K2f1KepSKz2dJLoI79Nqg40IsYt; SUHB=0M2VZj_NSAVG7w; SSOLoginState=1521095629; _T_WM=5ad11550fbf1922d3534220fe93e26c0',
        'Host':'weibo.cn',
		'Upgrade-Insecure-Requests':'1',
		'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36'    
		}  

    req = Request(url=url, headers=headers)  
    
    html = -1 # 如果返回 -1，说明爬取失败， 那么马上 进行数据的存储
    
    # 解决爬取失败问题
    try:
        html = urlopen(req).read().decode('utf-8')
    except Exception:
        return html
    return html

############################################################### 

'''
用beautifulsoap 修补一下网页
'''
def fix_html(html_str):
    # 修补html
    soup = BeautifulSoup(html_str,'html.parser', from_encoding="gb18030")
    fixed_html = soup.prettify()
    
    return fixed_html

############################################################### 
    
'''
对网页内容进行解析，得到
1、昵称
2、主页地址
3、所在地区（详细地址）
4、点赞数，转发数，评论数
5、发微博的时间
6、微博内容
7、地址
8、性别

获取还有多少页没有爬的信息

返回爬取完一个页面后得到的 微博集合(microblog_quene) + 下页信息

下页信息，如果 == -1，那么说明到了最后一页，如果没到，则返回下页页码，继续爬取
    如果 == -2 ，那么在爬取性别和地址的时候爬取失败，要及时存储数据，退出程序


'''
def parse_main_content(html_str):
    
    # 解析每一条微博
    microblog_quene = []
    
    soup = BeautifulSoup(html_str)
    
    # 获取包含 class 为 c ，存在id属性的 div  很重要
    microblog_soups = soup.find_all('div', attrs = {'class' : 'c'}, id = re.compile('.*'))
    
    # 获取页面信息，看看还有多少页面没有爬取
    page_info = soup.find('div',attrs = {'class' : 'pa'}).get_text().strip()
    
    nextpage = -1

    if page_info.find('下页') == -1: # 没有找到下页，说明到了最后一页
        return microblog_quene, nextpage 
    else:
        re_str = r'[1-9][0-9]*/[1-9][0-9]*页'  ## 匹配的结果  1/100页
        ss = re.findall(re_str, page_info)[0]
        
        # 获取下一页
        nextpage = int(ss[0 : ss.find('/')]) + 1
 
    # 对每一条blog进行遍历爬取
    for microblog_soup in microblog_soups:
        
        # 获取昵称
        nickname = microblog_soup.find('a',attrs = {'class' : 'nk'}).get_text().strip()
        # print('nickname : ' + nickname + '\n')
        
        # 获取用户主页  https://weibo.cn/a813689091
        index = microblog_soup.find('a',attrs = {'class' : 'nk'}).get('href').strip()
        # print('index : ' + index + '\n')
        
        # 地址和性别
        sex,location = parse_user(index)
        
        if sex == -1: #爬取失败
            nextpage = -2
            return microblog_quene, nextpage
        
        # 获取用户内容,内容中间有很多空格，需要删减
        # content需要分 是转发的，还是原创的
        divs = microblog_soup.find_all('div')
        ss = ''
        flag = 0 # 表示不是转发的 2 表示是转发的  双重保险，只有出现了 ‘转发理由’ 和 ‘转发了’，才能证明这条微博是转发的
        aim_div = divs[0]
        for div in divs:
            ss = div.get_text().strip()
            if ss.find('转发理由:') != -1 or ss.find('转发了') != -1:
                if ss.find('转发理由:') != -1: # 确认是转发的微博后定位到内容div
                    aim_div = div
                flag = flag + 1
            
        if flag == 2: # 表示这条微博是转发的
            ss = aim_div.get_text().strip()
            content = ss[ss.find('转发理由') + 5 : ss.find('赞[0]')]
        else: # 这条微博是原创的微博
            content = microblog_soup.find('span',attrs = {'class' : 'ctt'}).get_text().strip()
        
        # print('content:' + content + '\n')

        # 获取时间   03月15日 23:26
        time = microblog_soup.find('span',attrs = {'class' : 'ct'}).get_text().strip()
        time = time[:12]
        # print('time:' + time + '\n')
        
        ## 用来匹配评论数、转发数等数字
        re_num = '[0-9]*'
        
        # 获取点赞数  例如：0
        re_str = u'https://weibo.cn/attitude.*' # 正则表达式，用来匹配href的值
        thumb_up = microblog_soup.find('a', href = re.compile(re_str)).get_text().strip()
        thumb_up_count = int(re.findall(re_num,thumb_up[2:])[0])
        # print('thumb_up_count:' + str(thumb_up_count) + '\n')
    

        # 获取转发数  例如：0
        re_str = u'https://weibo.cn/repost.*'  # 正则表达式，用来匹配href的值
        repost = microblog_soup.find('a', href = re.compile(re_str)).get_text().strip()
        repost_count = int(re.findall(re_num,repost[3:])[0])
        # print('repost_count:' + str(repost_count) + '\n')

        # 获取评论数  例如：0
        re_str = u'https://weibo.cn/comment.*' # 正则表达式，用来匹配href的值
        # 如果用户转发了别人的微博，那么这里评论会有两个，第一个是原文评论，第二个才是用户的评论
        comment = microblog_soup.find_all('a', attrs = {'class' : 'cc'}, href = re.compile(re_str))
        commentlen = len(comment)
        if commentlen == 1: # 不是转发
            comment = comment[0].get_text().strip()
        else:
            comment = comment[1].get_text().strip()
        
        comment_count = int(re.findall(re_num,comment[3:])[0])
        
        # print('comment_count:' + str(comment_count ) + '\n')
         
        # print('============================================================')
 
        # new 一个微博的类,装入上面爬取到的信息
        microblog_item = microblog.microblog()
        
        microblog_item.set_neckname(nickname)
        microblog_item.set_index(index)
        microblog_item.set_location(location)
        microblog_item.set_comment_count(comment_count)
        microblog_item.set_sex(sex)
        microblog_item.set_repost_count(repost_count)
        microblog_item.set_thumb_up_count(thumb_up_count)
        microblog_item.set_time(time)
        microblog_item.set_content(content)
        
        microblog_quene.append(microblog_item)
        
    return microblog_quene, nextpage

############################################################### 
        
'''
根据用户主页的url，爬取用户的相关信息，例如性别、所在地等信息
还可以爬取更多信息，例如学历，是否为大V
返回性别和位置
'''
def parse_user(url):
    
    # 获取原网页
    html_source = downloadHtml(url)
    
    if html_source == -1:
        return html_source, html_source
        
    # 修补网页
    fixed_html = fix_html(html_source)
    
    soup = BeautifulSoup(fixed_html)
    
    user_soup = soup.find('div',attrs = {'class' : 'u'})
    
    # 性别和地址所在的字符串
    sex_location = user_soup.find('span',attrs = {'class' : 'ctt'}).get_text().strip()
    
    # 写正则表达式取出性别和地址
    re_str = r'男/.{0,6}|女/.{0,8}'
    sex_location = re.findall(re_str,sex_location)[0]
    sex = sex_location[:1]
    location = sex_location[2:]

    #print(sex)
    #print(location)
    #print("-----------------------------------")
    
    return sex,location

      
############################################################### 
# test  
    
############################################################### 
##设置url
    
ori = 'https://weibo.cn/search/?advancedfilter=1'

keyword = "苹果手机"
url_keyword = 'keyword=' + quote(keyword)  # 必须是英文或者中文转码，也就是说必须是ASCII

start_time = 'starttime=20180303'

end_time = 'endtime=20180318'

sort = 'sort=time'

smblog = '搜索'
url_smblog = 'smblog=' +  quote(smblog)  

#rand 会变，每换一个话题，都要在浏览器中重新获取rand值
rand = 'rand=9881'
others = 'p=r&' + rand + '&p=r'


url = set_url(ori,url_keyword, start_time, end_time, sort, url_smblog, others)

##############################################################

# 爬取第一个页面
# 打印出url，方便分析
print("第一个爬取的url: \n" + url)

# 获取原网页
html_source = downloadHtml(url)

if html_source == -1:
    print("-------------爬取失败-------------")
    sys.exit()

# 修补网页
fixed_html = fix_html(html_source)

microblogs =  []

microblog_quene, nextpage = parse_main_content(fixed_html)

# 合并爬取到的BLOG
microblogs = microblogs + microblog_quene

##############################################################
# 开始爬取 第 n 页  n >= 2
while nextpage != -1:
    # 由于第一个页面没有明确的下一页的url，所以还是在浏览器中测试，然后，找到下一页的规律
    # 下面的链接，nextpage是重点，其他和之前的没啥区别
    next_url = 'https://weibo.cn/search/mblog?hideSearchFrame=&' + \
    url_keyword +  '&advancedfilter=1&' + start_time + '&' + \
    end_time + '&' + sort + '&' + 'page=' + str(nextpage)
    
    print('\n\n------------第 ' + str(nextpage) + ' 页-------------- \n\n')
    print('next_url ： \n' + next_url + '\n\n')

    html_source = downloadHtml(next_url)
    if html_source == -1: # 爬取失败
        print("-------------爬取失败 -1-------------")
        break
    fixed_html = fix_html(html_source)
    microblog_quene, nextpage = parse_main_content(fixed_html)
    
    if nextpage == -2: # 爬取失败,在爬取个人主页的时候失败
        print("-------------爬取失败 -2-------------")
        break
    
    microblogs = microblogs + microblog_quene
    
    # 延时，防止被反爬虫，这个时间需要不断测试，达到一个平衡点
    sleep_time = random.randint(20,25)
    time.sleep(sleep_time)

print('一共爬取的microblogs数量 : ' + str(len(microblogs)))

path = "C:\\Users\\wansho\\Desktop\\微博数据.csv"
attrs = ['昵称','性别','所在地','时间','内容','点赞数','转发数','评论数','主页']
my_io.init_csv(path,attrs)

my_io.write_csv(path,microblogs)
    

'''
## 存储网页
write_path = 'C:\\Users\\wansho\\Desktop\\源网页.html'
my_io.write_html(fixed_html,write_path)
'''