# -*- coding: utf-8 -*-

# Standard library imports
# Third party imports
from django import forms
from django.contrib.auth.models import AnonymousUser
from django.core.urlresolvers import reverse
from django.db.models import get_model
from faker import Factory as FakerFactory
from haystack.management.commands import clear_index
from haystack.management.commands import rebuild_index
from haystack.query import SearchQuerySet

# Local application / specific library imports
from machina.apps.forum_search.forms import SearchForm
from machina.conf import settings as machina_settings
from machina.core.loading import get_class
from machina.core.utils import refresh
from machina.test.factories import create_category_forum
from machina.test.factories import create_forum
from machina.test.factories import create_topic
from machina.test.factories import PostFactory
from machina.test.factories import UserFactory
from machina.test.testcases import BaseClientTestCase

faker = FakerFactory.create()

Post = get_model('forum_conversation', 'Post')
Topic = get_model('forum_conversation', 'Topic')

PermissionHandler = get_class('forum_permission.handler', 'PermissionHandler')
assign_perm = get_class('forum_permission.shortcuts', 'assign_perm')
get_anonymous_user = get_class('forum_permission.shortcuts', 'get_anonymous_user')


class TestFacetedSearchView(BaseClientTestCase):
    def setUp(self):
        super(TestFacetedSearchView, self).setUp()

        # Permission handler
        self.perm_handler = PermissionHandler()

        # Set up the following forum tree:
        #
        #     top_level_cat
        #         forum_1
        #         forum_2
        #             forum_2_child_1
        #     top_level_forum_1
        #     top_level_forum_2
        #         sub_cat
        #             sub_sub_forum
        #     top_level_forum_3
        #         forum_3
        #             forum_3_child_1
        #                 forum_3_child_1_1
        #                     deep_forum
        #     last_forum
        #
        self.top_level_cat = create_category_forum()

        self.forum_1 = create_forum(parent=self.top_level_cat)
        self.forum_2 = create_forum(parent=self.top_level_cat)
        self.forum_2_child_1 = create_forum(parent=self.forum_2)

        self.top_level_forum_1 = create_forum()

        self.top_level_forum_2 = create_forum()
        self.sub_cat = create_category_forum(parent=self.top_level_forum_2)
        self.sub_sub_forum = create_forum(parent=self.sub_cat)

        self.top_level_forum_3 = create_forum()
        self.forum_3 = create_forum(parent=self.top_level_forum_3)
        self.forum_3_child_1 = create_forum(parent=self.forum_3)
        self.forum_3_child_1_1 = create_forum(parent=self.forum_3_child_1)
        self.deep_forum = create_forum(parent=self.forum_3_child_1_1)

        self.last_forum = create_forum()

        # Set up a topic and some posts
        self.topic_1 = create_topic(forum=self.forum_1, poster=self.user)
        self.post_1 = PostFactory.create(topic=self.topic_1, poster=self.user)
        self.topic_2 = create_topic(forum=self.forum_2, poster=self.user)
        self.post_2 = PostFactory.create(topic=self.topic_2, poster=self.user)
        self.topic_3 = create_topic(forum=self.forum_2_child_1, poster=self.user)
        self.post_3 = PostFactory.create(topic=self.topic_3, poster=self.user)

        # Assign some permissions
        assign_perm('can_read_forum', self.user, self.top_level_cat)
        assign_perm('can_read_forum', self.user, self.forum_1)
        assign_perm('can_read_forum', self.user, self.forum_2)
        assign_perm('can_read_forum', self.user, self.forum_2_child_1)
        assign_perm('can_read_forum', self.user, self.top_level_forum_1)

        self.sqs = SearchQuerySet()

        rebuild_index.Command().handle(interactive=False, verbosity=-1)

    def tearDown(self):
        clear_index.Command().handle(interactive=False, verbosity=-1)

    def test_can_search_forum_posts(self):
        # Setup
        correct_url = reverse('forum-search:search')
        get_data = {'q': self.topic_1.subject}
        # Run
        response = self.client.get(correct_url, data=get_data)
        # Check
        self.assertIsOk(response)
        self.assertEqual(len(response.context['page'].object_list), 1)
        self.assertEqual(response.context['page'].object_list[0].object, self.post_1)
