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
	######################################################################################
#                                                                                    #
#	                     FMovies.to (BY LinusOS400) - v0.01                          #
#                                                                                    #
######################################################################################


GOOD_RESPONSE_CODES = ['200','206']

TITLE = "FMovies.to"
PREFIX = "/video/FMovies"
ART = "art-default.jpg"
ICON = "icon-default.png"
ICON_LIST = "icon-list.png"
ICON_COVER = "icon-cover.png"
ICON_SEARCH = "icon-search.png"
ICON_SEARCH_QUE = "icon-search-queue.png"
ICON_NEXT = "icon-next.png"
ICON_MOVIES = "icon-movies.png"
ICON_MOVIES_FILTER = "icon-filter.png"
ICON_MOVIES_GENRE = "icon-genre.png"
ICON_MOVIES_LATEST = "icon-latest.png"
ICON_QUEUE = "icon-bookmark.png"
ICON_UNAV = "MoviePosterUnavailable.jpg"
ICON_PREFS = "icon-prefs.png"
ICON_UPDATE = "icon-update.png"
ICON_UPDATE_NEW = "icon-update-new.png"
ICON_SERIES = "icon-series.png"
ICON_CINEMA = "icon-cinema.png"
ICON_QUEUE = "icon-queue.png"
BASE_URL = "https://www.xmovies8.org"
######################################################################################
# Set global variables

def Start():

	ObjectContainer.title1 = TITLE
	ObjectContainer.art = R(ART)
	DirectoryObject.thumb = R(ICON_COVER)
	DirectoryObject.art = R(ART)
	VideoClipObject.thumb = R(ICON_COVER)
	VideoClipObject.art = R(ART)
	
	HTTP.CacheTime = CACHE_1HOUR
	HTTP.Headers['User-Agent'] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/31.0.1650.63 Safari/537.36"
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

# Collects 50 results per page, paginates by groups of 10
@route(PREFIX + "/showcategory")
def ShowCategory(title, page_count, key):

	oc = ObjectContainer(title2 = title + ' | ' + key + ' | Page ' + str(page_count))
	if title == 'Filter by Year':
		page_data = HTML.ElementFromURL(BASE_URL + '/' + key + '_movies?page=%s' % page_count)
	elif title == 'Filter by Genre':
		page_data = HTML.ElementFromURL(BASE_URL + '/' + key + '_movies?page=%s' % page_count)
		
	elem = page_data.xpath(".//div[@class='video_container b_10']//div[@class='cell_container']")
	
	try:
		last_page_no = page_data.xpath(".//div[@class='clearboth left']//ul//li[last()]//text()")[0]
		if last_page_no == '>>':
			last_page_no = page_count + 1
		else:
			last_page_no = int(last_page_no)
	except:
		pass
		
	for each in elem:
		url = BASE_URL + each.xpath(".//div[@class='thumb']//a//@href")[0]
		#Log("url -------- " + url)
		ttitle = each.xpath(".//div[@class='video_title']//a//text()")[0]
		#Log("ttitle -------- " + ttitle)
		thumb = "http:" + each.xpath(".//div[@class='thumb']//a//@src")[0]
		#Log("thumb -------- " + thumb)
		
		summary = 'Plot Summary on Movie Page'
		try:
			summary = 'Runtime : '
			summary_elems = each.xpath(".//div[@class='cell']//text()")
			for sume in summary_elems:
				if 'cdata' not in sume.lower() and sume.strip() <> '' and ttitle not in sume:
					summary = summary + sume + ' | '
			summary = (summary + ' Plot Summary on Movie Page').replace('-','').replace('| :', ':').replace(': |',':')
			#Log("summary -------- " + summary)
		except:
			pass

		oc.add(DirectoryObject(
			key = Callback(EpisodeDetail, title = ttitle, url = url, thumb = thumb, summary = summary),
			title = ttitle,
			summary = summary,
			thumb = Resource.ContentsOfURLWithFallback(url = thumb)
			)
		)
	if int(page_count) < last_page_no:
		oc.add(NextPageObject(
			key = Callback(ShowCategory, title = title, page_count = int(page_count) + 1, key = key),
			title = "Next Page (" + str(int(page_count) + 1) + ") >>",
			thumb = R(ICON_NEXT)
			)
		)
	else:
		oc.add(DirectoryObject(key = Callback(ShowMenu, title = 'Movies'), title = '<< Movies', thumb = R(ICON_MOVIES)))

	if len(oc) == 0:
		return ObjectContainer(header=title, message='No More Videos Available')
	return oc


######################################################################################


@route(PREFIX + "/showMenu")
def ShowMenu(title):

	oc2 = ObjectContainer(title2=title)
	oc2.add(DirectoryObject(key = Callback(SortMenu, title = 'Popular Movies', page_count = 1), title = 'Popular Movies', thumb = R(ICON_MOVIES_FILTER)))
	oc2.add(DirectoryObject(key = Callback(SortMenu, title = 'Latest Movies', page_count = 1), title = 'Latest Movies', thumb = R(ICON_MOVIES_FILTER)))
	oc2.add(DirectoryObject(key = Callback(SortMenu, title = 'Most Watched Movies', page_count = 1), title = 'Most Watched Movies', thumb = R(ICON_MOVIES_FILTER)))
	oc2.add(DirectoryObject(key = Callback(SortMenu, title = 'Filter by Genre', page_count = 1), title = 'Filter by Genre', thumb = R(ICON_MOVIES_GENRE)))
	oc2.add(DirectoryObject(key = Callback(SortMenu, title = 'Filter by Year', page_count = 1), title = 'Filter by Year', thumb = R(ICON_MOVIES_LATEST)))
	oc2.add(DirectoryObject(key = Callback(MainMenu), title = 'Main Menu', thumb = R(ICON)))

	return oc2

######################################################################################
@route(PREFIX + "/sortMenu")
def SortMenu(title, page_count):

	oc = ObjectContainer(title2 = title)
	
	if title == 'Filter by Year':
		page_data = HTML.ElementFromURL(BASE_URL)			
		elem = page_data.xpath(".//li[@class='dropdown'][1]//ul[@class='dropdown-menu multi-column']//li")
		for years in elem:
			key = years.xpath(".//text()")[0]

			oc.add(DirectoryObject(
				key = Callback(ShowCategory, title = title, page_count = page_count, key = key),
				title = key
				)
			)
	elif title == 'Filter by Genre':
		page_data = HTML.ElementFromURL(BASE_URL)			
		elem = page_data.xpath(".//li[@class='dropdown'][2]//ul[@class='dropdown-menu multi-column']//li")
		for genre in elem:
			key = genre.xpath(".//text()")[0]

			oc.add(DirectoryObject(
				key = Callback(ShowCategory, title = title, page_count = page_count, key = key),
				title = key
				)
			)
	else:
		oc = ObjectContainer(title2 = title + ' | Page ' + str(page_count))
		
		if title == 'Popular Movies':
			page_data = HTML.ElementFromURL(BASE_URL + '/popular_movies?page=%s' % page_count)
		elif title == 'Latest Movies':
			page_data = HTML.ElementFromURL(BASE_URL + '/latest_movies?page=%s' % page_count)
		elif title == 'Most Watched Movies':
			page_data = HTML.ElementFromURL(BASE_URL + '/most_watched_movies?page=%s' % page_count)	
		
		elem = page_data.xpath(".//div[@class='video_container b_10']//div[@class='cell_container']")
		
		try:
			last_page_no = page_data.xpath(".//div[@class='clearboth left']//ul//li[last()]//text()")[0]
			if last_page_no == '>>':
				last_page_no = page_count + 1
			else:
				last_page_no = int(last_page_no)
		except:
			pass
			
		for each in elem:
			url = BASE_URL + each.xpath(".//div[@class='thumb']//a//@href")[0]
			#Log("url -------- " + url)
			ttitle = each.xpath(".//div[@class='video_title']//a//text()")[0]
			#Log("ttitle -------- " + ttitle)
			thumb = "http:" + each.xpath(".//div[@class='thumb']//a//@src")[0]
			#Log("thumb -------- " + thumb)

			summary = 'Plot Summary on Movie Page'
			try:
				summary = 'Runtime : '
				summary_elems = each.xpath(".//div[@class='cell']//text()")
				for sume in summary_elems:
					if 'cdata' not in sume.lower() and sume.strip() <> '' and ttitle not in sume:
						summary = summary + sume + ' | '
				summary = (summary + ' Plot Summary on Movie Page').replace('-','').replace('| :', ':').replace(': |',':')
				#Log("summary -------- " + summary)
			except:
				pass

			oc.add(DirectoryObject(
				key = Callback(EpisodeDetail, title = ttitle, url = url, thumb = thumb, summary = summary),
				title = ttitle,
				summary = summary,
				thumb = Resource.ContentsOfURLWithFallback(url = thumb)
				)
			)
		if int(page_count) < last_page_no:
			oc.add(NextPageObject(
				key = Callback(SortMenu, title = title, page_count = int(page_count) + 1),
				title = "Next Page (" + str(int(page_count) + 1) + ") >>",
				thumb = R(ICON_NEXT)
				)
			)
		else:
			oc.add(DirectoryObject(key = Callback(ShowMenu, title = 'Movies'), title = '<< Movies', thumb = R(ICON_MOVIES)))
	
	if len(oc) == 0:
		return ObjectContainer(header=title, message='No More Videos Available')
	return oc
	

######################################################################################
# Creates page url from category and creates objects from that page

@route(PREFIX + "/showcategory")
def ShowCategory(title, page_count, key):

	oc = ObjectContainer(title2 = title + ' | ' + key + ' | Page ' + str(page_count))
	if title == 'Filter by Year':
		page_data = HTML.ElementFromURL(BASE_URL + '/' + key + '_movies?page=%s' % page_count)
	elif title == 'Filter by Genre':
		page_data = HTML.ElementFromURL(BASE_URL + '/' + key + '_movies?page=%s' % page_count)
		
	elem = page_data.xpath(".//div[@class='video_container b_10']//div[@class='cell_container']")
	
	try:
		last_page_no = page_data.xpath(".//div[@class='clearboth left']//ul//li[last()]//text()")[0]
		if last_page_no == '>>':
			last_page_no = page_count + 1
		else:
			last_page_no = int(last_page_no)
	except:
		pass
		
	for each in elem:
		url = BASE_URL + each.xpath(".//div[@class='thumb']//a//@href")[0]
		#Log("url -------- " + url)
		ttitle = each.xpath(".//div[@class='video_title']//a//text()")[0]
		#Log("ttitle -------- " + ttitle)
		thumb = "http:" + each.xpath(".//div[@class='thumb']//a//@src")[0]
		#Log("thumb -------- " + thumb)
		
		summary = 'Plot Summary on Movie Page'
		try:
			summary = 'Runtime : '
			summary_elems = each.xpath(".//div[@class='cell']//text()")
			for sume in summary_elems:
				if 'cdata' not in sume.lower() and sume.strip() <> '' and ttitle not in sume:
					summary = summary + sume + ' | '
			summary = (summary + ' Plot Summary on Movie Page').replace('-','').replace('| :', ':').replace(': |',':')
			#Log("summary -------- " + summary)
		except:
			pass

		oc.add(DirectoryObject(
			key = Callback(EpisodeDetail, title = ttitle, url = url, thumb = thumb, summary = summary),
			title = ttitle,
			summary = summary,
			thumb = Resource.ContentsOfURLWithFallback(url = thumb)
			)
		)
	if int(page_count) < last_page_no:
		oc.add(NextPageObject(
			key = Callback(ShowCategory, title = title, page_count = int(page_count) + 1, key = key),
			title = "Next Page (" + str(int(page_count) + 1) + ") >>",
			thumb = R(ICON_NEXT)
			)
		)
	else:
		oc.add(DirectoryObject(key = Callback(ShowMenu, title = 'Movies'), title = '<< Movies', thumb = R(ICON_MOVIES)))

	if len(oc) == 0:
		return ObjectContainer(header=title, message='No More Videos Available')
	return oc

######################################################################################

@route(PREFIX + "/episodedetail")
def EpisodeDetail(title, url, thumb, summary):

	summary = re.sub(r'[^0-9a-zA-Z \-/.,\':+&!()]', '?', summary)
	title = title.replace('–',' : ')
	title = unicode(title)
	oc = ObjectContainer(title2 = title, art = thumb)

	page_data = HTML.ElementFromURL(url)
	elem = page_data.xpath(".//div[preceding::div[@class='title clearboth']]//text()")
	summary = elem[0]
	
	#Test
	ref = url.split('#')[0].replace('www.','')
	vID = ref.split('v=')[1]
	#Log("vID: " + vID)
	#Log("Referer: " + ref)
	post_values = {'v': vID}
	h = {'referer': ref}
	data = JSON.ObjectFromURL('https://xmovies8.org/video_info/iframe', values=post_values, headers=h, method='POST')
	#Log(str(data))
	
	try:
		sortable_list = []
		for res, vUrl in data.items():
			vUrl = vUrl.replace('//html5player.org/embed?url=','')
			vUrl = urllib2.unquote(vUrl).decode('utf8') 
			sortable_list.append({'res': int(res),'vUrl':vUrl})
		sortable_list = sorted(sortable_list, reverse=True)
		
		for item in sortable_list:
			res = str(item['res']) + 'p'
			vUrl = str(item['vUrl'])
			
			#Log("vUrl ---------- " + vUrl)
			status = ' - [Offline]'
			if GetHttpStatus(vUrl) in GOOD_RESPONSE_CODES:
				status = ' - [Online]'
			try:
				oc.add(VideoClipObject(
					url = vUrl + '&VidRes=' + res + '&VidRes=' + title + '&VidRes=' + summary + '&VidRes=' + thumb,
					title = title + ' - ' + res + status,
					thumb = thumb,
					art = thumb,
					summary = summary
					)
				)
			except:
				pass
	except:
		pass
		
	if Check(title=title,url=url):
		oc.add(DirectoryObject(
			key = Callback(RemoveBookmark, title = title, url = url),
			title = "Remove Bookmark",
			summary = 'Removes the current movie from the Boomark que',
			thumb = R(ICON_QUEUE)
		)
	)
	else:
		oc.add(DirectoryObject(
			key = Callback(AddBookmark, title = title, url = url, summary=summary, thumb=thumb),
			title = "Bookmark Video",
			summary = 'Adds the current movie to the Bookmark que',
			thumb = R(ICON_QUEUE)
		)
	)

	return oc

######################################################################################
# Loads bookmarked shows from Dict.  Titles are used as keys to store the show urls.

@route(PREFIX + "/bookmarks")
def Bookmarks(title):

	oc = ObjectContainer(title1=title)

	for each in Dict:
		longstring = Dict[each]
		
		if 'https:' in longstring and 'Key4Split' in longstring:	
			stitle = longstring.split('Key4Split')[0]
			url = longstring.split('Key4Split')[1]
			summary = longstring.split('Key4Split')[2]
			thumb = longstring.split('Key4Split')[3]

			oc.add(DirectoryObject(
				key=Callback(EpisodeDetail, title=stitle, url=url, thumb=thumb, summary=summary),
				title=stitle,
				thumb=thumb,
				summary=summary
				)
			)
				
	#add a way to clear bookmarks list
	oc.add(DirectoryObject(
		key = Callback(ClearBookmarks),
		title = "Clear Bookmarks",
		thumb = R(ICON_QUEUE),
		summary = "CAUTION! This will clear your entire bookmark list!"
		)
	)

	if len(oc) == 0:
		return ObjectContainer(header=title, message='No Bookmarked Videos Available')
	return oc

######################################################################################
# Checks a show to the bookmarks list using the title as a key for the url
@route(PREFIX + "/checkbookmark")
def Check(title, url):
	longstring = Dict[title]
	#Log("url-----------" + url)
	if longstring != None and (longstring.lower()).find(TITLE.lower()) != -1:
		return True
	return False

######################################################################################
# Adds a movie to the bookmarks list using the title as a key for the url

@route(PREFIX + "/addbookmark")
def AddBookmark(title, url, summary, thumb):
	Dict[title] = title + 'Key4Split' + url +'Key4Split'+ summary + 'Key4Split' + thumb
	Dict.Save()
	return ObjectContainer(header=title, message='This movie has been added to your bookmarks.')

######################################################################################
# Removes a movie to the bookmarks list using the title as a key for the url

@route(PREFIX + "/removebookmark")
def RemoveBookmark(title, url):
	del Dict[title]
	Dict.Save()
	return ObjectContainer(header=title, message='This movie has been removed from your bookmarks.', no_cache=True)

######################################################################################
# Clears the Dict that stores the bookmarks list

@route(PREFIX + "/clearbookmarks")
def ClearBookmarks():

	remove_list = []
	for each in Dict:
		try:
			url = Dict[each]
			if url.find(TITLE.lower()) != -1 and 'http' in url:
				remove_list.append(each)
		except:
			continue

	for bookmark in remove_list:
		try:
			del Dict[bookmark]
		except Exception as e:
			Log.Error('Error Clearing Bookmarks: %s' %str(e))
			continue

	Dict.Save()
	return ObjectContainer(header="My Bookmarks", message='Your bookmark list will be cleared soon.', no_cache=True)

######################################################################################
# Clears the Dict that stores the search list

@route(PREFIX + "/clearsearches")
def ClearSearches():

	remove_list = []
	for each in Dict:
		try:
			if each.find(TITLE.lower()) != -1 and 'MyCustomSearch' in each:
				remove_list.append(each)
		except:
			continue

	for search_term in remove_list:
		try:
			del Dict[search_term]
		except Exception as e:
			Log.Error('Error Clearing Searches: %s' %str(e))
			continue

	Dict.Save()
	return ObjectContainer(header="Search Queue", message='Your Search Queue list will be cleared soon.', no_cache=True)

####################################################################################################
@route(PREFIX + "/search")
def Search(query, page_count=1):

	last_page_no = page_count
	Dict[TITLE.lower() +'MyCustomSearch'+query] = query
	Dict.Save()
	oc = ObjectContainer(title2='Search Results')

	try:
		furl = BASE_URL
		if page_count > 1:
			furl = BASE_URL + '/results?page=%s&q=%s' % (str(page_count), String.Quote(query, usePlus=True))

		data = HTTP.Request(furl + '&q=%s' % String.Quote(query, usePlus=True), headers="").content
		page_data = HTML.ElementFromString(data)
		elem = page_data.xpath(".//div[@class='video_container b_10']//div[@class='cell_container']")
		
		for each in elem:
			url = BASE_URL + each.xpath(".//div[@class='thumb']//a//@href")[0]
			#Log("url -------- " + url)
			ttitle = each.xpath(".//div[@class='video_title']//a//text()")[0]
			#Log("ttitle -------- " + ttitle)
			thumb = "http:" + each.xpath(".//div[@class='thumb']//a//@src")[0]
			#Log("thumb -------- " + thumb)
			summary = each.xpath(".//div[@class='video_quality']//text()")[0]
			#Log("summary -------- " + summary)
			
			oc.add(DirectoryObject(
				key = Callback(EpisodeDetail, title = ttitle, url = url, thumb = thumb, summary = summary),
				title = ttitle,
				summary = summary,
				thumb = Resource.ContentsOfURLWithFallback(url = thumb)
				)
			)
		
		try:
			last_page_no = page_data.xpath(".//div[@class='clearboth left']//ul//li[last()]//text()")[0]
			if last_page_no == '>>':
				last_page_no = page_count + 1
			else:
				last_page_no = int(last_page_no)
		except:
			pass
	except:
		pass
		
	if len(oc) == 0:
		return ObjectContainer(header='Search Results', message='No More Videos Available')
		
	oc.add(InputDirectoryObject(key = Callback(Search, page_count=1), title='Search', summary='Search Movies', prompt='Search for...', thumb=R(ICON_SEARCH)))
	if int(page_count) < last_page_no:
		oc.add(NextPageObject(
			key = Callback(Search, query = query, page_count = int(page_count) + 1),
			title = "Next Page (" + str(int(page_count) + 1) + ") >>",
			thumb = R(ICON_NEXT)
			)
		)
	else:	
		if int(page_count) > 2:
			oc.add(DirectoryObject(key = Callback(ShowMenu, title = 'Movies'), title = '<< Movies', thumb = R(ICON_MOVIES)))

	return oc

####################################################################################################
@route(PREFIX + "/searchQueueMenu")
def SearchQueueMenu(title):
	oc2 = ObjectContainer(title2='Search Using Term')
	#add a way to clear bookmarks list
	oc2.add(DirectoryObject(
		key = Callback(ClearSearches),
		title = "Clear Search Queue",
		thumb = R(ICON_SEARCH),
		summary = "CAUTION! This will clear your entire search queue list!"
		)
	)
	for each in Dict:
		query = Dict[each]
		#Log("each-----------" + each)
		#Log("query-----------" + query)
		try:
			if each.find(TITLE.lower()) != -1 and 'MyCustomSearch' in each and query != 'removed':
				oc2.add(DirectoryObject(key = Callback(Search, query = query, page_count=1), title = query, thumb = R(ICON_SEARCH))
			)
		except:
			pass

	return oc2
	
####################################################################################################
# Get HTTP response code (200 == good)
@route(PREFIX + '/gethttpstatus')
def GetHttpStatus(url):
	try:
		conn = urllib2.urlopen(url, timeout = global_request_timeout)
		resp = str(conn.getcode())
	except StandardError:
		resp = '0'
	#Log(url + " : " + resp)
	return resp
