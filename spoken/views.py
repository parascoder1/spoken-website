from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext
from django.shortcuts import render
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.context_processors import csrf
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.conf import settings
from forms import *
import json
from creation.views import get_video_info
from creation.models import TutorialCommonContent, TutorialDetail, TutorialResource

def home(request):
    #messages.success(request, "User has already in the attendance list")
    context = {}
    return render(request, 'spoken/templates/home.html', context)

def get_or_query(terms, search_fields):
    #terms = ['linux', ' operating system', ' computers', ' hardware platforms', ' oscad']
    #search_fields = ['keyword']
    query = None
    for term in terms:
        or_query = None # Query to search for a given term in each field
        for field_name in search_fields:
            q = Q(**{"%s__icontains" % field_name: term})
            if or_query is None:
                or_query = q
            else:
                or_query = or_query | q
        if query is None:
            query = or_query
        else:
            query = query | or_query
    print query
    return query

def keyword_search(request):
    context = {}
    keyword = ''
    collection = None
    conjunction_words = ['a', 'i']
    form = TutorialSearchForm()
    if request.method == 'GET' and 'q' in request.GET and request.GET['q'] != '':
        form = KeywordSearchForm(request.GET)
        if form.is_valid():
            keyword = request.GET['q']
            keywords = keyword.split(' ')
            search_fields = ['keyword']
            remove_words = set(keywords).intersection(set(conjunction_words))
            for key in remove_words:
                keywords.remove(key)
            query = get_or_query(keywords, search_fields)
            if query:
                collection = TutorialResource.objects.filter(common_content = TutorialCommonContent.objects.filter(query), language = Language.objects.filter(name='English'))
        
    context = {}
    context['form'] = KeywordSearchForm()
    context['collection'] = collection
    context['keywords'] = keyword
    context.update(csrf(request))
    return render(request, 'spoken/templates/keyword_search.html', context)

def tutorial_search(request):
    context = {}
    collection = None
    form = TutorialSearchForm()
    if request.method == 'POST':
        form = TutorialSearchForm(request.POST)
        if form.is_valid():
            lang = form.cleaned_data['language']
            foss = form.cleaned_data['foss_category']
            if not lang and foss:
                collection = TutorialResource.objects.filter(tutorial_detail__foss_id = foss)
            elif lang and not foss:
                collection = TutorialResource.objects.filter(language_id = lang)
            elif foss and lang:
                collection = TutorialResource.objects.filter(tutorial_detail__foss_id = foss, language_id = lang)
            
    context['form'] = form
    context['collection'] = collection
    context.update(csrf(request))
    return render(request, 'spoken/templates/tutorial_search.html', context)

def watch_tutorial(request, foss, tutorial, lang):
    try:
        td_rec = TutorialDetail.objects.get(foss = FossCategory.objects.get(foss = foss.replace('-', ' ')), tutorial = tutorial.replace('-', ' '))
        tr_rec = TutorialResource.objects.select_related().get(tutorial_detail = td_rec, language = Language.objects.get(name = lang))
        tr_recs = TutorialResource.objects.select_related().filter(tutorial_detail__in = TutorialDetail.objects.filter(foss = tr_rec.tutorial_detail.foss).order_by('order').values_list('id'), language = tr_rec.language)
    except Exception, e:
        messages.error(request, str(e))
        return HttpResponseRedirect('/')
    video_path = settings.MEDIA_ROOT + "videos/" + str(tr_rec.tutorial_detail.foss_id) + "/" + str(tr_rec.tutorial_detail_id) + "/" + tr_rec.video
    video_info = get_video_info(video_path)
    context = {
        'tr_rec': tr_rec,
        'tr_recs': sorted(tr_recs, key=lambda tutorial_resource: tutorial_resource.tutorial_detail.order),
        'video_info': video_info,
        'media_url': settings.MEDIA_URL,
        'media_path': settings.MEDIA_ROOT,
        'tutorial_path': str(tr_rec.tutorial_detail.foss_id) + '/' + str(tr_rec.tutorial_detail_id) + '/',
        'script_base': settings.SCRIPT_URL
    }
    return render(request, 'spoken/templates/watch_tutorial.html', context)

@csrf_exempt
def get_language(request):
    if request.method == "POST":
        foss = request.POST.get('foss')
        lang = request.POST.get('lang')
        output = ''
        if not lang and foss:
            collection = TutorialResource.objects.select_related('Language').filter(tutorial_detail__foss_id = foss).values_list('language__id', 'language__name').distinct()
            tmp = '<option value = ""> -- Select Language -- </option>'
            for i in collection:
                tmp +='<option value='+str(i[0])+'>'+i[1]+'</option>'
            output = ['foss', tmp]
            return HttpResponse(json.dumps(output), mimetype='application/json')
            
        elif lang and not foss:
            collection = TutorialResource.objects.filter(language_id = lang).values_list('tutorial_detail__foss__id', 'tutorial_detail__foss__foss').distinct()
            tmp = '<option value = ""> -- Select Foss -- </option>'
            for i in collection:
                tmp +='<option value='+str(i[0])+'>'+i[1]+'</option>'
            output = ['lang', tmp]
            return HttpResponse(json.dumps(output), mimetype='application/json')
            
        elif foss and lang:
            pass
