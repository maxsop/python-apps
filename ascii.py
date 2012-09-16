import os
import webapp2
import jinja2
import urllib2
from xml.dom import minidom

from google.appengine.ext import db

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)

#use this google-map API to get geo-position image
GMAPS_URL = "http://maps.googleapis.com/maps/api/staticmap?size=380x263&sensor=false&"
def gmaps_img(points):
    markers = '&'.join('markers=%s,%s' % (p.lat, p.lon) for p in points)
    return GMAPS_URL + markers

#use this API from hostip.info to get ip info
IP_URL = "http://api.hostip.info/?ip="
def get_cords(ip):
    #ip = "4.2.2.2" #hard-coded this for testing only
    url = IP_URL + ip
    content = None
    try:
        content = urllib2.urlopen(url).read()
    except urllib2.URLError:
        return #geo-cordinate is broken or something

    if content:
        #parse the xml and find the coordinates
        return geo_coords(content)

#Parsing xml docs
def geo_coords(xml):
    x = minidom.parseString(xml)
    coords = x.getElementsByTagName("gml:coordinates")
    if coords and coords[0].childNodes[0].nodeValue:#check if there's a tag element and if valid
        a, b = x.getElementsByTagName("gml:coordinates")[0].childNodes[0].nodeValue.split(',')
        return db.GeoPt(b,a)

class BaseHandler(webapp2.RequestHandler):

        def write(self, *a, **kw):
                self.response.out.write(*a, **kw)

        def render_str(self, template, **params):
                t = jinja_env.get_template(template)
                return t.render(params)

        def render(self, template, **kw):
                self.write(self.render_str(template, **kw))

class Art(db.Model):
	title = db.StringProperty(required = True)
	art = db.TextProperty(required = True)
	created = db.DateTimeProperty(auto_now_add = True)
	coords = db.GeoPtProperty()	

class MainPage(BaseHandler):
    def render_front(self, title="", art="", error=""):

        arts = db.GqlQuery("SELECT * FROM Art ORDER BY created DESC LIMIT 10")
        arts = list(arts)# just to prevent the running of multiple querries
        #check if we have coordinates points
        #point = []
        #[points.append(a.coords) for a in arts if arts.coords is not None]
        points = filter(None, (a.coords for a in arts))

        #if we have any arts coords, make an image url and display it
        img_url = None
        if points:
            img_url = gmaps_img(points)

        self.render('front.html', title=title, art=art, error=error, arts=arts, img_url = img_url)

    def get(self):
        #self.write(repr(get_cords(self.request.remote_addr))) # fetching my ip for testing purpose only. Should be deleted later on
        self.render_front()

    def post(self):
    	title = self.request.get('title')
    	art = self.request.get('art')

    	if title and art:
                a = Art(title = title, art = art)
                #request user ip address
                coords = get_cords(self.request.remote_addr)
                if coords:#if we have coordinates add them to db object(Art)
                    a.coords = coords
                a.put()
                self.redirect('/')
    	else:
                error = "We need both a title and some artwork!"
                self.render("front.html", error=error)


app = webapp2.WSGIApplication([('/', MainPage)], debug=True)
