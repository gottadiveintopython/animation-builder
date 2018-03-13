# -*- coding: utf-8 -*-

__all__ = ('Compiler', )


from kivy.animation import Animation


class Compiler:

    SPECIAL_KEYWORDS = 'eval locals globals'.split()

    def __init__(self, database):
        self.special_keyword_preparers = {
            keyword + ': ': getattr(self, 'prepare_' + keyword)
            for keyword in self.SPECIAL_KEYWORDS
        }
        self.database = {
            key: self.prepare_dictionary(data)
            for key, data in database.items()
        }
        self.locals = None
        self.globals = None

    def compile(self, key):
        return self.compile_identifier(key)

    def compile_identifier(self, identifier):
        data, func_compile = self.database[identifier]
        return func_compile(data)

    def compile_simple(self, dictionary):
        copied = dictionary.copy()
        copied.update({
            key: func_compile(data)
            for key, (data, func_compile, ) in dictionary['special_keyword'].items()
        })
        del copied['special_keyword']
        return Animation(**copied)

    def compile_sequential(self, dictionary):
        anims = (func_compile(data) for (data, func_compile, ) in dictionary['sequential'])
        r = sum(anims, next(anims))

        copied = dictionary.copy()
        copied.update({
            key: func_compile(data)
            for key, (data, func_compile, ) in dictionary['special_keyword'].items()
        })
        del copied['special_keyword']
        del copied['sequential']

        for key, value in copied.items():
            setattr(r, key, value)
        return r

    def compile_parallel(self, dictionary):
        anims = (func_compile(data) for (data, func_compile, ) in dictionary['parallel'])
        r = next(anims)
        for anim in anims:
            r &= anim
        return r

    def raise_exception_unsupported_data(self, data):
        raise Exception(
            "Unsupported data type: " + str(type(data)))

    def compile_eval(self, codeobject):
        return eval(codeobject, self.globals, self.locals)

    def compile_locals(self, key):
        return self.locals[key]

    def compile_globals(self, key):
        return self.globals[key]

    def prepare_eval(self, string):
        return (compile(string, '<string>', 'eval'), self.compile_eval)

    def prepare_locals(self, string):
        return (string, self.compile_locals)

    def prepare_globals(self, string):
        return (string, self.compile_globals)

    def prepare_dictionary(self, dictionary):
        # replace short-form with long-form
        temp = dictionary.pop('S', None)
        if temp is not None:
            dictionary['sequential'] = temp
        temp = dictionary.pop('P', None)
        if temp is not None:
            dictionary['parallel'] = temp
        # check SPECIAL_KEYWORDS
        special_keyword = {}
        for key, value in dictionary.items():
            if isinstance(value, str):
                for prefix, func_prepare in self.special_keyword_preparers.items():
                    if value.startswith(prefix):
                        special_keyword[key] = func_prepare(value[len(prefix):])
        dictionary['special_keyword'] = special_keyword
        # sequential
        sequential = dictionary.get('sequential')
        if sequential is not None:
            dictionary['sequential'] = self.prepare_list(sequential)
            return (dictionary, self.compile_sequential, )
        # parallel
        parallel = dictionary.get('parallel')
        if parallel is not None:
            dictionary['parallel'] = self.prepare_list(parallel)
            return (dictionary, self.compile_parallel, )
        # simple
        return (dictionary, self.compile_simple)

    def prepare_list(self, listobj):
        return [
            self.prepare_string(item) if isinstance(item, str)
            else self.prepare_dictionary(item) if isinstance(item, dict)
            else self.raise_exception_unsupported_data(item)
            for item in listobj
        ]

    def prepare_string(self, string):
        for prefix, func_prepare in self.special_keyword_preparers.items():
            if string.startswith(prefix):
                return func_prepare(string[len(prefix):])
        return (string, self.compile_identifier)
