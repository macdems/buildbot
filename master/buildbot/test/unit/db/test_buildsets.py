# This file is part of Buildbot.  Buildbot is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# Copyright Buildbot Team Members


import datetime
import json
from unittest import mock

from twisted.internet import defer
from twisted.trial import unittest

from buildbot.db import buildsets
from buildbot.test import fakedb
from buildbot.test.fake import fakemaster
from buildbot.test.reactor import TestReactorMixin
from buildbot.util import UTC
from buildbot.util import datetime2epoch
from buildbot.util import epoch2datetime


class Tests(TestReactorMixin, unittest.TestCase):
    @defer.inlineCallbacks
    def setUp(self):
        self.setup_test_reactor()
        self.master = yield fakemaster.make_master(self, wantDb=True)
        self.db = self.master.db

        self.now = 9272359
        self.reactor.advance(self.now)

        # set up a sourcestamp with id 234 for use below
        yield self.db.insert_test_data([
            fakedb.SourceStamp(id=234),
            fakedb.Builder(id=1, name='bldr1'),
            fakedb.Builder(id=2, name='bldr2'),
        ])

    @defer.inlineCallbacks
    def test_addBuildset_getBuildset(self):
        bsid, _ = yield self.db.buildsets.addBuildset(
            sourcestamps=[234],
            reason='because',
            properties={},
            builderids=[1],
            external_idstring='extid',
            waited_for=False,
        )

        # TODO: verify buildrequests too
        bsdict = yield self.db.buildsets.getBuildset(bsid)
        self.assertIsInstance(bsdict, buildsets.BuildSetModel)
        self.assertEqual(
            bsdict,
            buildsets.BuildSetModel(
                bsid=bsid,
                external_idstring='extid',
                reason='because',
                submitted_at=datetime.datetime(1970, 4, 18, 7, 39, 19, tzinfo=UTC),
                results=-1,
                sourcestamps=[234],
            ),
        )

    @defer.inlineCallbacks
    def test_addBuildset_getBuildset_explicit_submitted_at(self):
        bsid_brids = yield self.db.buildsets.addBuildset(
            sourcestamps=[234],
            reason='because',
            properties={},
            builderids=[1],
            external_idstring='extid',
            submitted_at=epoch2datetime(8888888),
            waited_for=False,
        )
        bsdict = yield self.db.buildsets.getBuildset(bsid_brids[0])

        self.assertIsInstance(bsdict, buildsets.BuildSetModel)
        self.assertEqual(
            bsdict,
            buildsets.BuildSetModel(
                bsid=bsid_brids[0],
                external_idstring='extid',
                reason='because',
                sourcestamps=[234],
                submitted_at=datetime.datetime(1970, 4, 13, 21, 8, 8, tzinfo=UTC),
                results=-1,
            ),
        )

    @defer.inlineCallbacks
    def do_test_getBuildsetProperties(self, buildsetid, rows, expected):
        yield self.db.insert_test_data(rows)
        props = yield self.db.buildsets.getBuildsetProperties(buildsetid)

        self.assertEqual(props, expected)

    def test_getBuildsetProperties_multiple(self):
        return self.do_test_getBuildsetProperties(
            91,
            [
                fakedb.Buildset(id=91, complete=0, results=-1, submitted_at=0),
                fakedb.BuildsetProperty(
                    buildsetid=91, property_name='prop1', property_value='["one", "fake1"]'
                ),
                fakedb.BuildsetProperty(
                    buildsetid=91, property_name='prop2', property_value='["two", "fake2"]'
                ),
            ],
            {"prop1": ('one', 'fake1'), "prop2": ('two', 'fake2')},
        )

    def test_getBuildsetProperties_empty(self):
        return self.do_test_getBuildsetProperties(
            91,
            [
                fakedb.Buildset(id=91, complete=0, results=-1, submitted_at=0),
            ],
            {},
        )

    def test_getBuildsetProperties_nosuch(self):
        "returns an empty dict even if no such buildset exists"
        return self.do_test_getBuildsetProperties(91, [], {})

    @defer.inlineCallbacks
    def test_getBuildset_incomplete_zero(self):
        yield self.db.insert_test_data([
            fakedb.Buildset(
                id=91,
                complete=0,
                complete_at=0,
                results=-1,
                submitted_at=266761875,
                external_idstring='extid',
                reason='rsn',
            ),
            fakedb.BuildsetSourceStamp(buildsetid=91, sourcestampid=234),
        ])
        bsdict = yield self.db.buildsets.getBuildset(91)

        self.assertIsInstance(bsdict, buildsets.BuildSetModel)
        self.assertEqual(
            bsdict,
            buildsets.BuildSetModel(
                bsid=91,
                external_idstring='extid',
                reason='rsn',
                sourcestamps=[234],
                submitted_at=datetime.datetime(1978, 6, 15, 12, 31, 15, tzinfo=UTC),
                complete=False,
                complete_at=epoch2datetime(0),
                results=-1,
            ),
        )

    @defer.inlineCallbacks
    def test_getBuildset_complete(self):
        yield self.db.insert_test_data([
            fakedb.Buildset(
                id=91,
                complete=1,
                complete_at=298297875,
                results=-1,
                submitted_at=266761875,
                external_idstring='extid',
                reason='rsn',
            ),
            fakedb.BuildsetSourceStamp(buildsetid=91, sourcestampid=234),
        ])
        bsdict = yield self.db.buildsets.getBuildset(91)

        self.assertIsInstance(bsdict, buildsets.BuildSetModel)
        self.assertEqual(
            bsdict,
            buildsets.BuildSetModel(
                bsid=91,
                external_idstring='extid',
                reason='rsn',
                sourcestamps=[234],
                submitted_at=datetime.datetime(1978, 6, 15, 12, 31, 15, tzinfo=UTC),
                complete=True,
                complete_at=datetime.datetime(1979, 6, 15, 12, 31, 15, tzinfo=UTC),
                results=-1,
            ),
        )

    @defer.inlineCallbacks
    def test_getBuildset_nosuch(self):
        bsdict = yield self.db.buildsets.getBuildset(91)

        self.assertEqual(bsdict, None)

    def insert_test_getBuildsets_data(self):
        return self.db.insert_test_data([
            fakedb.Buildset(
                id=91,
                complete=0,
                complete_at=298297875,
                results=-1,
                submitted_at=266761875,
                external_idstring='extid',
                reason='rsn1',
            ),
            fakedb.BuildsetSourceStamp(buildsetid=91, sourcestampid=234),
            fakedb.Buildset(
                id=92,
                complete=1,
                complete_at=298297876,
                results=7,
                submitted_at=266761876,
                external_idstring='extid',
                reason='rsn2',
            ),
            fakedb.BuildsetSourceStamp(buildsetid=92, sourcestampid=234),
        ])

    @defer.inlineCallbacks
    def test_getBuildsets_empty(self):
        bsdictlist = yield self.db.buildsets.getBuildsets()

        self.assertEqual(bsdictlist, [])

    @defer.inlineCallbacks
    def test_getBuildsets_all(self):
        yield self.insert_test_getBuildsets_data()
        bsdictlist = yield self.db.buildsets.getBuildsets()

        def bsdictKey(bsdict):
            return bsdict.reason

        for bsdict in bsdictlist:
            self.assertIsInstance(bsdict, buildsets.BuildSetModel)
        self.assertEqual(
            sorted(bsdictlist, key=bsdictKey),
            sorted(
                [
                    buildsets.BuildSetModel(
                        bsid=91,
                        external_idstring='extid',
                        reason='rsn1',
                        sourcestamps=[234],
                        submitted_at=datetime.datetime(1978, 6, 15, 12, 31, 15, tzinfo=UTC),
                        complete_at=datetime.datetime(1979, 6, 15, 12, 31, 15, tzinfo=UTC),
                        complete=False,
                        results=-1,
                    ),
                    buildsets.BuildSetModel(
                        bsid=92,
                        external_idstring='extid',
                        reason='rsn2',
                        sourcestamps=[234],
                        submitted_at=datetime.datetime(1978, 6, 15, 12, 31, 16, tzinfo=UTC),
                        complete_at=datetime.datetime(1979, 6, 15, 12, 31, 16, tzinfo=UTC),
                        complete=True,
                        results=7,
                    ),
                ],
                key=bsdictKey,
            ),
        )

    @defer.inlineCallbacks
    def test_getBuildsets_complete(self):
        yield self.insert_test_getBuildsets_data()
        bsdictlist = yield self.db.buildsets.getBuildsets(complete=True)

        for bsdict in bsdictlist:
            self.assertIsInstance(bsdict, buildsets.BuildSetModel)
        self.assertEqual(
            bsdictlist,
            [
                buildsets.BuildSetModel(
                    bsid=92,
                    external_idstring='extid',
                    reason='rsn2',
                    sourcestamps=[234],
                    submitted_at=datetime.datetime(1978, 6, 15, 12, 31, 16, tzinfo=UTC),
                    complete_at=datetime.datetime(1979, 6, 15, 12, 31, 16, tzinfo=UTC),
                    complete=True,
                    results=7,
                ),
            ],
        )

    @defer.inlineCallbacks
    def test_getBuildsets_incomplete(self):
        yield self.insert_test_getBuildsets_data()
        bsdictlist = yield self.db.buildsets.getBuildsets(complete=False)

        for bsdict in bsdictlist:
            self.assertIsInstance(bsdict, buildsets.BuildSetModel)
        self.assertEqual(
            bsdictlist,
            [
                buildsets.BuildSetModel(
                    bsid=91,
                    external_idstring='extid',
                    reason='rsn1',
                    sourcestamps=[234],
                    submitted_at=datetime.datetime(1978, 6, 15, 12, 31, 15, tzinfo=UTC),
                    complete_at=datetime.datetime(1979, 6, 15, 12, 31, 15, tzinfo=UTC),
                    complete=False,
                    results=-1,
                ),
            ],
        )

    @defer.inlineCallbacks
    def test_completeBuildset_already_completed(self):
        yield self.insert_test_getBuildsets_data()
        with self.assertRaises(buildsets.AlreadyCompleteError):
            yield self.db.buildsets.completeBuildset(bsid=92, results=6)

    @defer.inlineCallbacks
    def test_completeBuildset_missing(self):
        yield self.insert_test_getBuildsets_data()
        with self.assertRaises(buildsets.AlreadyCompleteError):
            yield self.db.buildsets.completeBuildset(bsid=93, results=6)

    @defer.inlineCallbacks
    def test_completeBuildset(self):
        yield self.insert_test_getBuildsets_data()
        yield self.db.buildsets.completeBuildset(bsid=91, results=6)
        bsdicts = yield self.db.buildsets.getBuildsets()

        bsdicts = [
            (
                bsdict.bsid,
                bsdict.complete,
                datetime2epoch(bsdict.complete_at),
                bsdict.results,
            )
            for bsdict in bsdicts
        ]
        self.assertEqual(sorted(bsdicts), sorted([(91, 1, self.now, 6), (92, 1, 298297876, 7)]))

    @defer.inlineCallbacks
    def test_completeBuildset_explicit_complete_at(self):
        yield self.insert_test_getBuildsets_data()
        yield self.db.buildsets.completeBuildset(
            bsid=91, results=6, complete_at=epoch2datetime(72759)
        )
        bsdicts = yield self.db.buildsets.getBuildsets()

        bsdicts = [
            (
                bsdict.bsid,
                bsdict.complete,
                datetime2epoch(bsdict.complete_at),
                bsdict.results,
            )
            for bsdict in bsdicts
        ]
        self.assertEqual(sorted(bsdicts), sorted([(91, 1, 72759, 6), (92, 1, 298297876, 7)]))

    def insert_test_getRecentBuildsets_data(self):
        return self.db.insert_test_data([
            fakedb.SourceStamp(id=91, branch='branch_a', repository='repo_a'),
            fakedb.Buildset(
                id=91,
                complete=0,
                complete_at=298297875,
                results=-1,
                submitted_at=266761875,
                external_idstring='extid',
                reason='rsn1',
            ),
            fakedb.BuildsetSourceStamp(buildsetid=91, sourcestampid=91),
            fakedb.Buildset(
                id=92,
                complete=1,
                complete_at=298297876,
                results=7,
                submitted_at=266761876,
                external_idstring='extid',
                reason='rsn2',
            ),
            fakedb.BuildsetSourceStamp(buildsetid=92, sourcestampid=91),
            # buildset unrelated to the change
            fakedb.Buildset(
                id=93,
                complete=1,
                complete_at=298297877,
                results=7,
                submitted_at=266761877,
                external_idstring='extid',
                reason='rsn2',
            ),
        ])

    @defer.inlineCallbacks
    def test_getRecentBuildsets_all(self):
        yield self.insert_test_getRecentBuildsets_data()
        bsdictlist = yield self.db.buildsets.getRecentBuildsets(
            2, branch='branch_a', repository='repo_a'
        )

        self.assertEqual(
            bsdictlist,
            [
                buildsets.BuildSetModel(
                    bsid=91,
                    external_idstring='extid',
                    reason='rsn1',
                    sourcestamps=[91],
                    submitted_at=datetime.datetime(1978, 6, 15, 12, 31, 15, tzinfo=UTC),
                    complete_at=datetime.datetime(1979, 6, 15, 12, 31, 15, tzinfo=UTC),
                    complete=False,
                    results=-1,
                ),
                buildsets.BuildSetModel(
                    bsid=92,
                    external_idstring='extid',
                    reason='rsn2',
                    sourcestamps=[91],
                    submitted_at=datetime.datetime(1978, 6, 15, 12, 31, 16, tzinfo=UTC),
                    complete_at=datetime.datetime(1979, 6, 15, 12, 31, 16, tzinfo=UTC),
                    complete=True,
                    results=7,
                ),
            ],
        )

    @defer.inlineCallbacks
    def test_getRecentBuildsets_one(self):
        yield self.insert_test_getRecentBuildsets_data()
        bsdictlist = yield self.db.buildsets.getRecentBuildsets(
            1, branch='branch_a', repository='repo_a'
        )

        self.assertEqual(
            bsdictlist,
            [
                buildsets.BuildSetModel(
                    bsid=92,
                    external_idstring='extid',
                    reason='rsn2',
                    sourcestamps=[91],
                    submitted_at=datetime.datetime(1978, 6, 15, 12, 31, 16, tzinfo=UTC),
                    complete_at=datetime.datetime(1979, 6, 15, 12, 31, 16, tzinfo=UTC),
                    complete=True,
                    results=7,
                ),
            ],
        )

    @defer.inlineCallbacks
    def test_getRecentBuildsets_zero(self):
        yield self.insert_test_getRecentBuildsets_data()
        bsdictlist = yield self.db.buildsets.getRecentBuildsets(
            0, branch='branch_a', repository='repo_a'
        )

        self.assertEqual(bsdictlist, [])

    @defer.inlineCallbacks
    def test_getRecentBuildsets_noBranchMatch(self):
        yield self.insert_test_getRecentBuildsets_data()
        bsdictlist = yield self.db.buildsets.getRecentBuildsets(
            2, branch='bad_branch', repository='repo_a'
        )

        self.assertEqual(bsdictlist, [])

    @defer.inlineCallbacks
    def test_getRecentBuildsets_noRepoMatch(self):
        yield self.insert_test_getRecentBuildsets_data()
        bsdictlist = yield self.db.buildsets.getRecentBuildsets(
            2, branch='branch_a', repository='bad_repo'
        )

        self.assertEqual(bsdictlist, [])

    @defer.inlineCallbacks
    def test_addBuildset_simple(self):
        (bsid, brids) = yield self.db.buildsets.addBuildset(
            sourcestamps=[234],
            reason='because',
            properties={},
            builderids=[2],
            external_idstring='extid',
            waited_for=True,
        )

        def thd(conn):
            # we should only have one brid
            self.assertEqual(len(brids), 1)

            # should see one buildset row
            r = conn.execute(self.db.model.buildsets.select())
            rows = [
                (
                    row.id,
                    row.external_idstring,
                    row.reason,
                    row.complete,
                    row.complete_at,
                    row.submitted_at,
                    row.results,
                )
                for row in r.fetchall()
            ]
            self.assertEqual(rows, [(bsid, 'extid', 'because', 0, None, self.now, -1)])

            # one buildrequests row
            r = conn.execute(self.db.model.buildrequests.select())
            self.assertEqual(
                r.keys(),
                [
                    'id',
                    'buildsetid',
                    'builderid',
                    'priority',
                    'complete',
                    'results',
                    'submitted_at',
                    'complete_at',
                    'waited_for',
                ],
            )
            self.assertEqual(r.fetchall(), [(bsid, brids[2], 2, 0, 0, -1, self.now, None, 1)])

            # one buildset_sourcestamps row
            r = conn.execute(self.db.model.buildset_sourcestamps.select())
            self.assertEqual(list(r.keys()), ['id', 'buildsetid', 'sourcestampid'])
            self.assertEqual(r.fetchall(), [(1, bsid, 234)])

        yield self.db.pool.do(thd)

    @defer.inlineCallbacks
    def test_addBuildset_bigger(self):
        props = {"prop": (['list'], 'test')}
        yield defer.succeed(None)
        xxx_todo_changeme1 = yield self.db.buildsets.addBuildset(
            sourcestamps=[234],
            reason='because',
            waited_for=False,
            properties=props,
            builderids=[1, 2],
        )

        (bsid, brids) = xxx_todo_changeme1

        def thd(conn):
            self.assertEqual(len(brids), 2)

            # should see one buildset row
            r = conn.execute(self.db.model.buildsets.select())
            rows = [
                (
                    row.id,
                    row.external_idstring,
                    row.reason,
                    row.complete,
                    row.complete_at,
                    row.results,
                )
                for row in r.fetchall()
            ]
            self.assertEqual(rows, [(bsid, None, 'because', 0, None, -1)])

            # one property row
            r = conn.execute(self.db.model.buildset_properties.select())
            rows = [(row.buildsetid, row.property_name, row.property_value) for row in r.fetchall()]
            self.assertEqual(rows, [(bsid, 'prop', json.dumps([['list'], 'test']))])

            # one buildset_sourcestamps row
            r = conn.execute(self.db.model.buildset_sourcestamps.select())
            rows = [(row.buildsetid, row.sourcestampid) for row in r.fetchall()]
            self.assertEqual(rows, [(bsid, 234)])

            # and two buildrequests rows (and don't re-check the default
            # columns)
            r = conn.execute(self.db.model.buildrequests.select())
            rows = [(row.buildsetid, row.id, row.builderid) for row in r.fetchall()]

            # we don't know which of the brids is assigned to which
            # buildername, but either one will do
            self.assertEqual(sorted(rows), [(bsid, brids[1], 1), (bsid, brids[2], 2)])

        yield self.db.pool.do(thd)

    @defer.inlineCallbacks
    def test_addBuildset_properties_cache(self):
        """
        Test that `addChange` properly seeds the `getChange` cache.
        """

        # Patchup the buildset properties cache so we can verify that
        # it got called form `addBuildset`.
        mockedCachePut = mock.Mock()
        self.patch(self.db.buildsets.getBuildsetProperties.cache, "put", mockedCachePut)

        # Setup a dummy set of properties to insert with the buildset.
        props = {"prop": (['list'], 'test')}

        # Now, call `addBuildset`, and verify that the above properties
        # were seed in the `getBuildsetProperties` cache.
        bsid, _ = yield self.db.buildsets.addBuildset(
            sourcestamps=[234],
            reason='because',
            properties=props,
            builderids=[1, 2],
            waited_for=False,
        )
        mockedCachePut.assert_called_once_with(bsid, props)
