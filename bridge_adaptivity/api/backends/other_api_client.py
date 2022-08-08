from datetime import datetime
import logging

from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from edx_rest_api_client.client import EdxRestApiClient
from requests import RequestException
from slumber.exceptions import HttpClientError

from api.backends.base_api_client import BaseApiClient


log = logging.getLogger(__name__)


class OtherApiClient(BaseApiClient, EdxRestApiClient):
    """API client to interact with other content course rou."""

    # TOKEN_URL = "/oauth2/access_token"

    def __init__(self, content_source):
        #  Removed this because of the BaseAPIClient get the content blocks from source to view the in bridge
        #TODO: Modify this according the other platform requirments
        BaseApiClient.__init__(self, content_source=content_source)
        log.debug("Creating new OpenEdx API client...")
        log.debug(self.content_source.host_url)
        # Currently we are removing Authentication for OtherAPIClient Prototype 
        # token_cache_key = f'api:{self.content_source.o_auth_client.client_id}:token'

        #access_token = cache.get(token_cache_key)
        # if not access_token:
        #     access_token, expires_at = self.get_oauth_access_token()
        #     ttl = expires_at - datetime.now()
        #     cache.set(token_cache_key, access_token, ttl.seconds)

        # EdxRestApiClient.__init__(self, self.url, jwt=access_token)

    @property
    def url(self):
        return f'{self.content_source.host_url}/api/courses/v1/'

    def get_oauth_access_token(self):
        url = "{host_url}{token_url}".format(
            host_url=self.content_source.host_url,
            token_url=self.TOKEN_URL
        )
        # # Modifing the URl token to overcome the authentication process
        # url = "{host_url}".format(
        #      host_url=self.content_source.host_url,
        #     #  token_url=self.TOKEN_URL
        # )
        log.debug("Requesting oauth token: (url={})".format(url))
        try:
            oauth_client = self.content_source.o_auth_client
            access_token, expires_at = super().get_oauth_access_token(
                url=url,
                client_id=oauth_client.client_id,
                client_secret=oauth_client.client_secret,
                token_type='jwt',
            )
        except ObjectDoesNotExist:
            raise HttpClientError(
                "OAuth token request failure. Please, configure OAuth client in order to be able make API requests."
            )
        except ValueError:
            log.exception(
                "You may want to check your OAuth registration on LTI Provider."
                "LTI Provider may be disabled (to enable: LMS config > FEATURES > ENABLE_OAUTH2_PROVIDER: true"
            )
            raise HttpClientError(
                "OAuth token request failure."
            )
        except RequestException:
            log.exception('OAuth2 token request to the OpenEdx LTI Provider failed.')
            raise HttpClientError(
                "OAuth token request failure."
            )
        return access_token, expires_at

    def get_course_blocks(self, course_id):
        blocks = super().get_course_blocks(course_id)
        filtered_blocks = ['sequential', 'course', 'chapter', 'vertical']
        return [block for block in blocks if block['type'] not in filtered_blocks]
