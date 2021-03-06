# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'House'
        db.create_table(u'houses_house', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=16)),
            ('mailing_list', self.gf('django.db.models.fields.CharField')(max_length=16, blank=True)),
        ))
        db.send_create_signal(u'houses', ['House'])

        # Adding model 'HouseMember'
        db.create_table(u'houses_housemember', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='housemember', to=orm['auth.User'])),
            ('term', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['base.Term'])),
            ('house', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['houses.House'])),
            ('is_leader', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'houses', ['HouseMember'])

        # Adding unique constraint on 'HouseMember', fields ['user', 'term']
        db.create_unique(u'houses_housemember', ['user_id', 'term_id'])

        # Adding unique constraint on 'HouseMember', fields ['term', 'house', 'is_leader']
        db.create_unique(u'houses_housemember', ['term_id', 'house_id', 'is_leader'])


    def backwards(self, orm):
        # Removing unique constraint on 'HouseMember', fields ['term', 'house', 'is_leader']
        db.delete_unique(u'houses_housemember', ['term_id', 'house_id', 'is_leader'])

        # Removing unique constraint on 'HouseMember', fields ['user', 'term']
        db.delete_unique(u'houses_housemember', ['user_id', 'term_id'])

        # Deleting model 'House'
        db.delete_table(u'houses_house')

        # Deleting model 'HouseMember'
        db.delete_table(u'houses_housemember')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'base.term': {
            'Meta': {'ordering': "('id',)", 'unique_together': "(('term', 'year'),)", 'object_name': 'Term'},
            'current': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.IntegerField', [], {'primary_key': 'True'}),
            'term': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'year': ('django.db.models.fields.PositiveSmallIntegerField', [], {})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'houses.house': {
            'Meta': {'object_name': 'House'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mailing_list': ('django.db.models.fields.CharField', [], {'max_length': '16', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '16'})
        },
        u'houses.housemember': {
            'Meta': {'unique_together': "(('user', 'term'), ('term', 'house', 'is_leader'))", 'object_name': 'HouseMember'},
            'house': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['houses.House']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_leader': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'term': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['base.Term']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'housemember'", 'to': u"orm['auth.User']"})
        }
    }

    complete_apps = ['houses']