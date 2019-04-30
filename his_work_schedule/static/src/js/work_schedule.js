odoo.define('his_work_schedule.work_schedule', function (require) {
    "use strict";

    var core = require('web.core');
    var Model = require('web.Model');
    var Widget = require('web.Widget');
    var Dialog = require('web.Dialog');
    var FormRelational = require('web.form_relational');
    var KanbanRecord = require('web_kanban.Record');
    var QWeb = core.qweb;

    KanbanRecord.include({
        events: _.defaults({
            'click .register_source i': 'delete_register_source'
        }, KanbanRecord.prototype.events),

        delete_register_source: function (e) {
            e.preventDefault();
            var self = this, $e = $(e.currentTarget);

            new Model(this.model).call("delete_register_source", {'id': this.id})
                .then(function (result) {
                    $e.parents('.o_kanban_record').remove();
                });

        },
        //on_card_clicked: function() {
        //    if (this.model === 'his.register_source') {
        //        debugger
        //        var action = {
        //            type: 'ir.actions.client',
        //            name: 'Confirm',
        //            tag: 'hr_attendance_kiosk_confirm',
        //            employee_id: this.record.id.raw_value,
        //            employee_name: this.record.name.raw_value,
        //            employee_state: this.record.attendance_state.raw_value,
        //        };
        //        this.do_action(action);
        //    } else {
        //        this._super.apply(this, arguments);
        //    }
        //}

    });

    //// TODO 要修改addons\web\static\src\js\views\form_relational_widgets.js文件，使其返回值中包括FieldOne2Many
    //FormRelational.FieldOne2Many.include({
    //    //start: function() {
    //    //    var result = this._super.apply(this, arguments);
    //    //    debugger
    //    //    var $e = $('<div class="btn btn-sm btn-primary re_generate">重新生成</div>');
    //    //    this.viewmanager.control_panel.$el.append($e);
    //    //    return result;
    //    //},
    //    //init: function(field_manager, node) {
    //    //    this._super(field_manager, node);
    //    //    debugger
    //    //
    //    //},
    //});


    Date.prototype.Format = function (fmt) { //author: meizz
        var o = {
            "M+": this.getMonth() + 1, //月份
            "d+": this.getDate(), //日
            "h+": this.getHours(), //小时
            "m+": this.getMinutes(), //分
            "s+": this.getSeconds(), //秒
            "q+": Math.floor((this.getMonth() + 3) / 3), //季度
            "S": this.getMilliseconds() //毫秒
        };
        if (/(y+)/.test(fmt)) fmt = fmt.replace(RegExp.$1, (this.getFullYear() + "").substr(4 - RegExp.$1.length));
        for (var k in o)
            if (new RegExp("(" + k + ")").test(fmt)) fmt = fmt.replace(RegExp.$1, (RegExp.$1.length == 1) ? (o[k]) : (("00" + o[k]).substr(("" + o[k]).length)));
        return fmt;
    };


    Dialog.include({
        open: function () {
            if (this.title == '号源') {
                this.$footer.remove();
            }
            return this._super.apply(this, arguments);
        }
    });

    var WorkSchedule = Widget.extend({
        events: {
            'click .department': 'change_department', //选择科室

            'mouseenter .on-edit': 'show_shift_type', //可编辑的单元格进入,显示班次面板

            'click .btn-edit': 'change_to_edit', //编辑数据
            'click .btn-cancel': 'change_to_normal', //取消编辑
            'click .btn-save': 'save_edit', //保存编辑

            'click .btn-shift-type': 'change_shift_type', //修改班次
            'click .btn-shift-recycle': 'clear_shift', //清空排班

            'click .btn-prev': 'change_date_prev', //上一个时间单位
            'click .btn-next': 'change_date_next', //下一个时间单位


            'click .fa-gear': 'show_time_range', // 显示时间段
            'click .fa-times': 'delete_shift' // 删除排班
        },
        // 显示时间段
        show_time_range: function (e) {
            e = $(e.currentTarget); //班次按钮
            var self = this;
            return this
                .rpc("/web/action/load", {action_id: "his_work_schedule.action_schedule_shift_tree1"})
                .then(function (result) {
                    result.res_id = e.data('id');
                    result.name = '号源';
                    result.context = JSON.stringify($.extend(JSON.parse(result.context || '{}'), {show_all: 1}));
                    return self.do_action(result);
                });
        },
        //清除班次安排
        clear_shift: function (e) {
            var shifts = this.get_shifts();
            if (shifts.length == 0)return;
            shifts.splice(0, shifts.length);//清空排班
            this.current_cell.html(QWeb.render("ShiftCellContent", {day: {shifts: shifts}}));
            this.changed = true;
        },
        // 删除排班
        delete_shift: function (e) {
            var $e = $(e.currentTarget), shift_id = $e.data('shift_id');
            var shifts = this.get_shifts();
            var shifts_render = [];
            for (var i = 0, l = shifts.length; i < l; i++) {
                if (shifts[i].shift_id == shift_id) {
                    if(shifts[i].id){
                        shifts[i].deleted = true
                    }
                    else{
                        shifts.splice(i, 1);
                    }
                }
                else{
                    if(!shifts[i].deleted){
                        shifts_render.push(shifts[i]);
                    }
                }
            }
            this.current_cell.html(QWeb.render("ShiftCellContent", {day: {shifts: shifts_render}}));
            this.changed = true;
        },
        change_shift_type: function (e) {
            var shift_id = $(e.currentTarget).data('id'); //班次ID

            var shifts = this.get_shifts(), shift_exist, shifts_render = [];
            shifts.forEach(function (shift) {
                if (shift.shift_id == shift_id){
                    if(shift.deleted){
                        //shift.deleted = false;
                    }
                    else{
                        shift_exist = true;
                    }
                }
                if(!shift.deleted)shifts_render.push(shift);
            });

            // 班次存在
            if (shift_exist)return;

            if (shifts_render.length > 2) {
                this.do_warn('错误', '每天排班数量不允许超过2个!');
                return
            }

            if(shifts_render.length == 2){
                this.current_cell.html(QWeb.render("ShiftCellContent", {day: {shifts: shifts_render}}));
                this.changed = true;
                return
            }

            var shift_type = this.work_schedule.shift_type.filter(function (item) {
                return item.id == shift_id
            })[0];

            shifts_render.push({
                shift_id: shift_type.id,
                start_time: shift_type.start_time,
                shift_name: shift_type.name,
                shift_color: shift_type.color
            });


            shifts.push({
                shift_id: shift_type.id,
                start_time: shift_type.start_time,
                shift_name: shift_type.name,
                shift_color: shift_type.color
            });

            // 按上班时间排序
            shifts_render.sort(function (x, y) {
                return x.start_time > y.start_time;
            });

            this.current_cell.html(QWeb.render("ShiftCellContent", {day: {shifts: shifts_render}}));


            this.changed = true;
        },
        change_date_next: function () {
            this.current_date = new Date(this.current_date.getTime() + 7 * 24 * 60 * 60 * 1000);
            this.reset_date_range(this.current_date);//重置日期范围

            if (!this.department_id)return;
            this.get_work_schedule();
        },
        change_date_prev: function () {
            this.current_date = new Date(this.current_date.getTime() - 7 * 24 * 60 * 60 * 1000);
            this.reset_date_range(this.current_date);//重置日期范围

            if (!this.department_id)return;
            this.get_work_schedule();
        },


        save_edit: function () {
            if (!this.changed) {
                this.reset_edit();
                return;
            }
            var self = this;
            this.model
                .call("change_work_schedule", {schedule: this.work_schedule.work_schedule, department_id: this.department_id})
                .then(function (result) {
                    self.get_work_schedule()
                });
        },
        change_to_edit: function () {
            this.editing = true;
            this.$el_btn_edit.css('display', 'none');
            this.$el_btn_save.css('display', 'inline-block');
            this.$el_btn_cancel.css('display', 'inline-block');

            this.$el.find('span').removeClass('saved');
        },
        //选择科室
        change_department: function (e) {
            var department_id = $(e.currentTarget).data('id');
            if (this.department_id == department_id)return;

            this.department_id = department_id;
            var department = this.departments.filter(function (item) {
                return department_id == item.id
            })[0];
            //显示科室名称
            this.$el_current_department.text(department.name);
            this.current_date = new Date();
            this.reset_date_range(this.current_date);
            //得到排班数据
            this.get_work_schedule();

        },
        //得到排班数据
        get_work_schedule: function () {
            var self = this;
            this.model
                .call("get_work_schedule", {
                    department_id: this.department_id,
                    start_date: this.start_date,
                    end_date: this.end_date
                })
                .then(function (result) {
                    self.work_schedule = result;
                    self.$el_content.html(QWeb.render("WorkScheduleDetail", result));
                    self.$el_shift_type_panel.html(QWeb.render("ShiftTypePanel", {shift_type: result.shift_type}));
                    //显示编辑按钮
                    self.reset_edit();
                });
        },

        reset_edit: function () {
            this.editing = false;
            this.changed = false; //排班是否改变

            //是否显示编辑按钮
            var show = false;
            this.work_schedule.work_schedule.forEach(function (schedule) {
                schedule.days.forEach(function (day) {
                    if (!day.expired)show = true;
                });
            });
            if (show)
                this.$el_btn_edit.css('display', 'inline-block');
            else {
                this.$el_btn_edit.css('display', 'none');
            }
            this.$el_btn_save.css('display', 'none');
            this.$el_btn_cancel.css('display', 'none');
            this.$el_shift_type_panel.css('display', 'none');

            var $td = $('.on-edit');
            $td.removeClass('on-edit-highlight');

            this.$el.find('span').addClass('saved');
        },
        change_to_normal: function () {
            if (!this.changed) {
                this.reset_edit();
                return;
            }
            this.get_work_schedule();
        },
        get_shifts: function () {
            var cell = this.current_cell, employee_id = cell.data('empl_id'), date = cell.data('date');//当前单元格

            var shifts;

            this.work_schedule.work_schedule.forEach(function (schedule) {
                schedule.days.forEach(function (day) {
                    if (day.date == date && day.empl_id == employee_id) {
                        shifts = day.shifts;
                    }
                })
            });
            return shifts;
        },
        //开始
        start: function () {
            var self = this;

            this.model = new Model("his.work_schedule");

            this.model.call("get_work_schedule_info", [])
                .then(function (result) {
                    self.departments = result;//所有科室

                    self.$el.html(QWeb.render("MyWorkSchedule1", {departments: result})); //渲染
                    self.$el.addClass('work_schedule_main');

                    self.$el_current_department = self.$('.current-department');
                    self.$el_btn_edit = self.$('.btn-edit');
                    self.$el_btn_save = self.$('.btn-save');
                    self.$el_btn_cancel = self.$('.btn-cancel');
                    self.$el_content = self.$('.work_schedule_content');
                    self.$el_current_group = self.$('.current-group');
                    self.$el_start_date = self.$('.start-date');
                    self.$el_end_date = self.$('.end-date');
                    self.$el_btn_current_date = self.$('.btn-current-date');
                    self.$el_shift_type_panel = self.$('.shift-type-panel');

                    self.editing = false;
                    self.current_date = new Date();
                    self.reset_date_range(self.current_date);//重置日期范围
                });


            return this._super.apply(this, arguments);
        },
        //重置日期范围
        reset_date_range: function (now) {

            var start_date, end_date, el_btn_current_date;
            var getYearWeek = function (a, b, c) {
                var date1 = new Date(a, parseInt(b) - 1, c), date2 = new Date(a, 0, 1),
                    d = Math.round((date1.valueOf() - date2.valueOf()) / 86400000);
                return Math.ceil((d + ((date2.getDay() + 1) - 1)) / 7);
            };

            var week = now.getDay();
            if (week == 0) {
                start_date = new Date(now.getTime() - 6 * 24 * 60 * 60 * 1000);
                end_date = new Date(now.getTime());
            }
            else {
                week -= 1;
                start_date = new Date(now.getTime() - week * 24 * 60 * 60 * 1000);
                end_date = new Date(start_date.getTime() + 6 * 24 * 60 * 60 * 1000);
            }
            el_btn_current_date = getYearWeek(start_date.getFullYear(), start_date.getMonth() + 1, start_date.getDate());
            el_btn_current_date = '第' + el_btn_current_date + '周(' + start_date.Format("MM-dd") + '到' + end_date.Format("MM-dd") + ')';


            this.start_date = start_date.Format("yyyy-MM-dd");
            this.end_date = end_date.Format("yyyy-MM-dd");

            this.$el_start_date.text(this.start_date);
            this.$el_end_date.text(this.end_date);
            this.$el_btn_current_date.text(el_btn_current_date);

        },
        destroy: function () {
            this._super.apply(this, arguments);
        },
        //可编辑的单元格进入,显示班次面板
        show_shift_type: function (e) {
            //处于编辑模式
            if (!this.editing)return;

            // 当前单元格添加样式
            var $td = $('.on-edit');
            $td.removeClass('on-edit-highlight');

            e = $(e.currentTarget);
            e.addClass('on-edit-highlight');

            // 浮动班次面板定位
            var p = e.offset();
            p.top += e.outerHeight();
            if (p.top + this.$el_shift_type_panel.outerHeight() > $(window).height()) {
                p.top = p.top - e.outerHeight() - this.$el_shift_type_panel.outerHeight() + 1;
                if (!this.$el_shift_type_panel.hasClass('shift-type-panel-top-border')) {
                    this.$el_shift_type_panel.addClass('shift-type-panel-top-border');
                }
                this.$el_shift_type_panel.removeClass('shift-type-panel-bottom-border');
            }
            else {
                if (!this.$el_shift_type_panel.hasClass('shift-type-panel-bottom-border')) {
                    this.$el_shift_type_panel.addClass('shift-type-panel-bottom-border');
                }
                this.$el_shift_type_panel.removeClass('shift-type-panel-top-border');
            }
            p.left = p.left + e.outerWidth() - this.$el_shift_type_panel.outerWidth() + 1;
            if (this.$el_shift_type_panel.css('display') == 'none') {
                this.$el_shift_type_panel.css('display', 'inline-block')
            }
            this.$el_shift_type_panel.offset(p);

            // 设定当前单元格
            this.current_cell = e;
        }
    });


    core.action_registry.add('work_schedule_manager_default', WorkSchedule);


});
