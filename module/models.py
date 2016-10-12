from django.db import models
from django.contrib.auth.models import User
from django.db.models import Max
import lti.utils

class Course(models.Model):
    '''
    Course
    '''
    name = models.CharField(max_length=200)

    def __unicode__(self):
        return "{}: {}".format(self.pk, self.name)


class Module(models.Model):
    '''
    Represents an "LTI box"
    '''
    # descriptive name, corresponds to edx subsection title
    name = models.CharField(max_length=200)

    def __unicode__(self):
        return "{}: {}".format(self.pk, self.name)

class UserModule(models.Model):
    '''
    One instance for each combination of user and module
    Used for keeping track of states (grade, last_position)
    '''
    user = models.ForeignKey(User)
    module = models.ForeignKey(Module)
    # student's running total score for module
    grade = models.FloatField(default=0)
    # position of last sequence_item loaded, take this out?
    last_position = models.PositiveIntegerField(default=1)
    completed = models.BooleanField(default=False)
    # full credit threshold for module; defined here so that it can be changed lti custom parameter screen
    max_points = models.FloatField(null=True)

    def recompute_grade(self):
        '''
        compute current score for module
        '''
        grade = 0
        for sequence_item in self.sequenceitem_set.all():
            attempts = sequence_item.attempt_set.all()
            if attempts.exists():
                grade = grade + attempts.aggregate(Max('points'))['points__max']
        self.grade = grade
        self.save(update_fields=['grade'])

        return grade

    def grade_passback(self):
        '''
        Grade passback to LMS, convert raw grade to a scaled grade between 0.0 and 1.0
        '''
        if not self.ltiparameters:
            return None

        # if points earned is greater than max_points, pass back maximum of 100%
        if self.max_points > 0 and self.grade < max_points:
            percent_grade = self.grade/self.max_points
        else:
            percent_grade = 1


        response = lti.utils.grade_passback(self, percent_grade)
        if response:
            print response.description
        return response

    def __unicode__(self):
        return "{}: username={}, module={}".format(
            self.pk,
            self.ltiparameters.lis_person_sourcedid,
            self.module.pk
        )


class Activity(models.Model):
    '''
    General model for items (questions/pages) served in a module
    '''
    name = models.CharField(max_length=200)
    module = models.ForeignKey(Module)
    # question lookup from grade input happends based on this field
    usage_id = models.CharField(max_length=200)
    # display url
    url = models.URLField(max_length=200)
    type = models.CharField(max_length=100, choices=(
        ('problem','problem'),
        ('html','html'),
    ))
    dependencies = models.ManyToManyField('Activity', blank=True)
    visible = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'Activities'

    def __unicode__(self):
        return "{}: {}".format(self.pk, self.name)



class SequenceItem(models.Model):
    '''
    each row represents the first time user visits a resource, in a module
    set of sequence items for a particular user/module represent problem history
    '''
    # user = models.ForeignKey(User)
    # module = models.ForeignKey(Module)
    user_module = models.ForeignKey(UserModule)

    # activity displayed for this sequence item
    activity = models.ForeignKey(Activity)
    # position within the module sequence this activity is displayed for the user
    position = models.PositiveIntegerField()
    timestamp_created = models.DateTimeField(null=True,auto_now=True)
    method = models.CharField(max_length=200,blank=True,default='')   # for storing a short description of the method used to select the activity
    # maximum running score for activity
    # grade = models.FloatField(default=0)

    # def __unicode__(self):
    #     return "{}: {}".format(self.pk, self.name)

    class Meta:
        unique_together = ('user_module','position')

    def __unicode__(self):
        return "{}: user={}, activity={}".format(
            self.pk, 
            self.user_module.ltiparameters.lis_person_sourcedid,
            self.activity.pk
        )


class Attempt(models.Model):
    '''
    Row for each time a student makes a problem attempt.
    Instances are also made when problems are submitted outside of LTI module context;
        this info kept in same model because they might be from students that may see the question later in the LTI module
    '''
    activity = models.ForeignKey(Activity)
    # TODO make this required
    user = models.ForeignKey(User,null=True,blank=True)
    # this model can store attempts for users not seen before
    username = models.CharField(max_length=200,null=True,blank=True)
    # user score for specific attempt
    points = models.FloatField()
    # number of points possible for problem
    max_points = models.FloatField()
    # time of attempt
    timestamp = models.DateTimeField(null=True,auto_now=True)
    # can be null, if this attempt is outside of a lti window
    sequence_item = models.ForeignKey(SequenceItem, null=True, blank=True)

    def __unicode__(self):
        return "{}: username={}, activity={}, score={}/{}".format(self.pk, self.username, self.activity.pk, self.points, self.max_points)

