odoo.define('hrp_queue.work_schedule', function (require) {
"use strict";

var core = require('web.core');
var Model = require('web.Model');
var Widget = require('web.Widget');

var QWeb = core.qweb;



var WorkSchedule = Widget.extend({
    events: {
        "click .edit": function() {

            var self = this;
//            this.$('.js_payment_info')
            new Model('hrp.schedule_manage').call('get_schedule_results', {'edit': 1}).then(function(result) {
                self.$el.html(QWeb.render("MyWorkSchedule", result));
            });
        },
        "click .cancel": function() {
            var self = this;
            new Model('hrp.schedule_manage').call('get_schedule_results').then(function(result) {
                self.$el.html(QWeb.render("MyWorkSchedule", result));
            });
        },

        "click .save": function() {
            var self = this;
            new Model('hrp.schedule_manage').call('get_schedule_results').then(function(result) {
                self.$el.html(QWeb.render("MyWorkSchedule", result));
            });
        },
        "click .schedule_cancel_button": function() {
            alert('qqq');
        },
        "mouseenter .scheduleitem": function(event) {
            debugger;
            var edit = this.$("#edit").text();

            if (edit == 1) {
                // 获取元素位子
                var top = event.currentTarget.offsetTop + event.currentTarget.offsetHeight + 82;
                var left = event.currentTarget.offsetLeft;
                this.$("#paiban_toolbar_container").css("left", left).css("top", top);
                this.$("#paiban_toolbar_container").show();
//                event.currentTarget.parentNode.style("background", "#FECA40");
            }
        },
        "mouseleave .scheduleitem": function(event) {
            var edit = this.$("#edit").text();

            if (edit == 1) {
                // 获取元素位子
                this.$("#paiban_toolbar_container").hide();
//                this.$("#paiban_toolbar_container").css("display", "none");
            }
        },
        "mouseenter #paiban_toolbar_container": function(event) {
            var edit = this.$("#edit").text();
            if (edit == 1) {
                this.$("#paiban_toolbar_container").show();
            }
        },
        "mouseleave #paiban_toolbar_container": function(event) {
            var edit = this.$("#edit").text();
            if (edit == 1) {
                this.$("#paiban_toolbar_container").hide();
            }
        },
    },



    start: function () {
        var self = this;
        new Model('hrp.schedule_manage').call('get_schedule_results', []).then(function(result) {
            self.$el.html(QWeb.render("MyWorkSchedule", result));
        });


//
//
//        var hr_employee = new Model('hr.employee');
//        hr_employee.query(['attendance_state', 'name'])
//            .filter([['user_id', '=', self.session.uid]])
//            .all()
//            .then(function (res) {
//                if (_.isEmpty(res) ) {
//                    self.$('.o_hr_attendance_employee').append(_t("Error : Could not find employee linked to user"));
//                    return;
//                }
//                self.employee = res[0];
//                self.$el.html(QWeb.render("MyWorkSchedule", {widget: self}));
//            });

        return this._super.apply(this, arguments);
    }

});

core.action_registry.add('schedule_result', WorkSchedule);

return WorkSchedule;

});
