######################################################################################
#                                                                                    #
#	                     FMovies.to (BY LinusOS400) - v0.01                          #
#                                                                                    #
######################################################################################

TITLE = "FMovies.to"
PREFIX = "/video/FMovies"
ART = "art-default.jpg"
ICON = "icon-default.png"
ICON_LIST = "icon-list.png"
ICON_COVER = "icon-cover.png"
ICON_SEARCH = "icon-search.png"
ICON_NEXT = "icon-next.png"
ICON_MOVIES = "icon-movies.png"
ICON_SERIES = "icon-series.png"
ICON_CINEMA = "icon-cinema.png"
ICON_QUEUE = "icon-queue.png"
BASE_URL = "http://fmovies.to"

######################################################################################

def Start():

    ObjectContainer.title1 = TITLE
    ObjectContainer.art = R(ART)
    DirectoryObject.thumb = R(ICON_COVER)
    DirectoryObject.art = R(ART)
    VideoClipObject.thumb = R(ICON_COVER)
    VideoClipObject.art = R(ART)
	
    HTTP.CacheTime = CACHE_1HOUR
	HTTP.Headers['User-Agent'] = "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:48.0) Gecko/20100101 Firefox/48.0"
    HTTP.Headers['Referer'] = BASE_URL

#######################################################################################
@handler(PREFIX, TITLE, art=ART, thumb=ICON)	
def MainMenu():

 	oc = ObjectContainer(title2=TITLE)
	oc.add(DirectoryObject(key = Callback(ShowMenu, title = 'Movies'), title = 'Movies', thumb = R(ICON_MOVIES)))
	oc.add(DirectoryObject(key = Callback(Bookmarks, title="Bookmarks"), title = "Bookmarks", thumb = R(ICON_QUEUE)))
	oc.add(DirectoryObject(key = Callback(SearchQueueMenu, title = 'Search Queue'), title = 'Search Queue', summary='Search using saved search terms', thumb = R(ICON_SEARCH_QUE)))
	oc.add(InputDirectoryObject(key = Callback(Search, page_count=1), title='Search', summary='Search Movies', prompt='Search for...', thumb=R(ICON_SEARCH)))
	try:
		if updater.update_available()[0]:
			oc.add(DirectoryObject(key = Callback(updater.menu, title='Update Plugin'), title = 'Update (New Available)', thumb = R(ICON_UPDATE_NEW)))
		else:
			oc.add(DirectoryObject(key = Callback(updater.menu, title='Update Plugin'), title = 'Update (Running Latest)', thumb = R(ICON_UPDATE)))
	except:
		pass
		
	return oc

######################################################################################
def DomainTest():

    if Dict['domain_test'] == 'Fail':
        message = '%s is NOT a Valid Site URL for this channel.  Please pick a different Site URL.'
        return MessageContainer('Error', message %Dict['site_url'])
    else:
        return False
		
######################################################################################		
@route(PREFIX + "/show/category")
def ShowCategory(title, category, href):
    """Creates page url from category and creates objects from that page"""

    if DomainTest() != False:
        return DomainTest()

    oc = ObjectContainer(title1=title)

    html = html_from_url(clean_url(href))

    for m in media_list(html, category):
        if category != '/tv-series':
            oc.add(DirectoryObject(
                key=Callback(EpisodeDetail, title=m['title'], url=m['url']),
                title=m['title'],
                thumb=Callback(get_thumb, url=m['thumb'])
                ))
        else:
            oc.add(DirectoryObject(
                key=Callback(TVShow, title=m['title'], thumb=m['thumb'], url=m['url']),
                title=m['title'],
                thumb=Callback(get_thumb, url=m['thumb'])
                ))

    nhref = next_page(html)
    if nhref:
        oc.add(NextPageObject(
            key=Callback(ShowCategory, title=title, category=category, href=nhref),
            title="More...",
            thumb=R(ICON_NEXT)
            ))

    if len(oc) != 0:
        return oc

    c = 'TV Series' if category == '/tv-series' else category[1:].title()
    return MessageContainer('Warning', '%s Category Empty' %c)
	
######################################################################################
	@route(PREFIX + "/film")
def film(title, thumb, url):
    """Return episode list if no season info, otherwise return season info"""

    if DomainTest() != False:
        return DomainTest()

    oc = ObjectContainer(title1=title)

    html = html_from_url(clean_url(url))

    info_node = html.xpath('//div[@id="nameinfo"]')
    if info_node:
        new_thumb = html.xpath('//img[@id="nameimage"]/@src')
        thumb = clean_url(new_thumb[0]) if new_thumb else thumb

        text_block = info_node[0].text_content()
        r = Regex(r'(?i)(season\s(\d+))').findall(text_block)
        if r:
            for season, i in r:
                oc.add(DirectoryObject(
                    key=Callback(SeasonDetail, title=season.title(), season=int(i), thumb=thumb, url=url),
                    title=season.title(),
                    thumb=Callback(get_thumb, url=thumb)
                    ))
        else:
            episode_list(oc, info_node, thumb)

    if len(oc) != 0:
        return oc

    return MessageContainer('Warning', 'No Show(s) Found')
	
####################################################################################
	def episode_list(oc, node, thumb, season=None):
    anode = node[0].xpath('./a')
    for i, a in enumerate(anode):
        href = a.get('href')
        if season:
            if int(href.rsplit('/', 2)[1][1:]) == season:
                etitle = a.text_content()
            else:
                continue
        else:
            try:
                s = node[0].xpath('./span')[i]
                etitle = a.text_content() + ' ' + s.text_content()
            except:
                etitle = a.text_content()

        oc.add(DirectoryObject(
            key=Callback(EpisodeDetail, title=etitle, url=href),
            title=etitle,
            thumb=Callback(get_thumb, url=thumb)
            ))
    return
	
###################################################################################
	@route(PREFIX + "/episode/detail")
def EpisodeDetail(title, url):
    """
    Gets metadata and google docs link from episode page.
    Checks for trailer availablity.
    """

    if DomainTest() != False:
        return DomainTest()

    oc = ObjectContainer(title1=title)

    try:
        html = html_from_url(clean_url(url))
    except Exception as e:
        Log.Critical('* EpisodeDetail Error: %s' %str(e))
        message = 'This media has expired.' if ('HTTP Error' in str(e) and '404' in str(e)) else str(e)
        return MessageContainer('Warning', message)

    ptitle = html.xpath("//title/text()")[0].rsplit(" Streaming",1)[0].rsplit(" Download",1)[0]
    thumb = html.xpath('//img[@id="nameimage"]/@src')
    thumb = (thumb[0] if thumb[0].startswith('http') else clean_url(thumb[0])) if thumb else None

    wpm = html.xpath('//iframe[@id="wpm"]/@src')
    if not wpm:
        return MessageContainer('Warning', 'No Video Source Found.')

    pass_html = html_from_url(clean_url(wpm[0]))
    video_urls = []
    source_iframe = pass_html.xpath('//iframe/@src')
    if source_iframe:
        part = 0
        if pass_html.xpath('//div[starts-with(@id, "part")]'):
            part = 1

        try:
            video_urls.append((part, html_from_url(clean_url(source_iframe[0])).xpath('//iframe/@src')[0]))
        except Exception as e:
            Log.Error('* EpisodeDetail Error: %s' %str(e))
            pass

        if part != 0:
            base_iframe = source_iframe[0].split('.php')[0]
            count = 1
            more = True
            while more and (count < 5):
                count += 1
                try:
                    video_urls.append((count, html_from_url(clean_url(base_iframe + '%i.php' %count)).xpath('//iframe/@src')[0]))
                except Exception as e:
                    Log.Warn('* EpisodeDetail Warning: %s' %str(e))
                    more = False

        for p, u in sorted(video_urls):
            if 'prx.proxy' in u:
                u = 'https://docs.google.com/file/' + u.split('/file/')[1]
            oc.add(VideoClipObject(
                title='%i-%s' %(p, ptitle) if p != 0 else ptitle,
                thumb=Callback(get_thumb, url=thumb),
                url=u
                ))

    trailpm = html.xpath('//iframe[@id="trailpm"]/@src')
    if trailpm:
        thtml = html_from_url(clean_url(trailpm[0]))
        yttrailer = thtml.xpath('//iframe[@id="yttrailer"]/@src')
        if yttrailer:
            yttrailer_url = yttrailer[0] if yttrailer[0].startswith('http') else 'https:' + yttrailer[0]
            if 'prx.proxy' in yttrailer_url:
                yttrailer_url = 'http://www.youtube.com/embed/' + yttrailer_url.split('/embed/')[1]
            oc.add(VideoClipObject(url=yttrailer_url, thumb=R(ICON_SERIES), title="Watch Trailer"))

    if len(oc) != 0:
        return oc

    return MessageContainer('Warning', 'No Media Found')
	
##################################################################################
	@route(PREFIX + "/genre/menu")
def GenreMenu(title):
    """Displays movie genre categories"""

    if DomainTest() != False:
        return DomainTest()

    oc = ObjectContainer(title1=title)

    html = html_from_url(clean_url('/movies/genre.php?showC=27'))
    for m in media_list(html, '/movies', genre=True):
        oc.add(DirectoryObject(
            key=Callback(ShowCategory, title=m['title'], category='/movies', href=m['url']),
            title=m['title'],
            thumb=Callback(get_thumb, url=m['thumb'])
            ))

    if len(oc) != 0:
        return oc

    return MessageContainer('Warning', 'No Genre(s) Found')
	
##################################################################################
@route(PREFIX + "/search", page=int)
def Search(query='', page=1):
    if DomainTest() != False:
        return DomainTest()

    query = query.strip()
    url = clean_url('/search.php?dayq=%s&page=%i' %(String.Quote(query, usePlus=True), page))

    oc = ObjectContainer(title1='Search for \"%s\"' %query)

    html = html_from_url(url)
    for m in media_list(html, '/search'):
        oc.add(DirectoryObject(
            key=Callback(EpisodeDetail, title=m['title'], url=m['url']),
            title=m['title'],
            thumb=Callback(get_thumb, url=m['thumb'])
            ))

    nhref = next_page(html)
    if nhref:
        oc.add(NextPageObject(
            key=Callback(Search, query=query, page=page+1),
            title="More...",
            thumb=R(ICON_NEXT)
            ))

    if len(oc) != 0:
        return oc

    return MessageContainer('Warning', 'Oops! No results were found. Please try a different word.')
###################################################################################
def media_list(html, category, genre=False):
    """didn't want to write this over-and-over again"""

    info_list = list()
    for each in html.xpath("//td[@class='topic_content']"):
        eid = int(Regex(r'goto\-(\d+)').search(each.xpath("./div/a/@href")[0]).group(1))
        if category == '/movies' or category == '/search':
            url = clean_url("/view.php?id=%i" %eid)
        else:
            url = clean_url("%s/view.php?id=%i" %(category, eid))

        thumb = each.xpath("./div/a/img/@src")[0]
        thumb = thumb if thumb.startswith('http') else clean_url(thumb)

        title = thumb.rsplit("/",1)[1].rsplit("-",1)[0] if genre else each.xpath("./div/a/img/@alt")[0]

        info_list.append({'title': title, 'thumb': thumb, 'url': url})

    return info_list

####################################################################################
def next_page(html):
    """Seperated out next page code just in case"""

    nhref = False
    next_page_node = html.xpath('//a[contains(@href, "&page=")][text()=">"]/@href')
    if next_page_node:
        nhref = next_page_node[0]

    return nhref

####################################################################################
def html_from_url(url):
    """pull down fresh content when site URL changes"""

    if Dict['site_url'] != Dict['site_url_old']:
        Dict['site_url_old'] = Dict['site_url']
        Dict.Save()
        HTTP.ClearCache()
        HTTP.Headers['Referer'] = Dict['site_url']

    return HTML.ElementFromURL(url)

####################################################################################
	def clean_url(href):
    """handle href/URL variations and set corrent Site URL"""

    if href.startswith('http') or href.startswith('//'):
        url = Dict['site_url'] + '/' + href.split('/', 3)[-1]
    else:
        url = Dict['site_url'] + (href if href.startswith('/') else '/' + href)

    return url
	
