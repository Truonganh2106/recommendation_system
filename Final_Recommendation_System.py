import json
import pandas as pd
import numpy as np
import pymongo
from bson import ObjectId, json_util
from sklearn.metrics.pairwise import cosine_similarity
from flask import Flask, request

mongo_connection_string = "mongodb+srv://commerce:commerce@cluster0.lygmgn5.mongodb.net/commerce?retryWrites=true&w=majority"

# Kết nối với MongoDB Atlas
client = pymongo.MongoClient(mongo_connection_string)
# client = pymongo.MongoClient("mongodb://localhost:27017/")
database = client["commerce"]
products = pd.DataFrame(list(database["products"].find()))
products.sort_values('rate', inplace=True)
popular_products = products[products['numberOfReviews'] >= 10]
final_df = products[products['_id'].isin(popular_products['_id'])]
pt = final_df.pivot_table(index='_id', columns='category', values='numberOfReviews')
# print(pt.index)
pt.replace(np.nan, 0, inplace=True)
similarity = cosine_similarity(pt)
def get_top_rated_products(product_id):
    if ObjectId(product_id) not in products['_id'].unique():
        print(f"Product ID {ObjectId(product_id)} không tồn tại trong danh sách sản phẩm.")
        return None
    target_product = products[products['_id'] == ObjectId(product_id)]
    target_category = target_product['category'].iloc[0]
    filtered_products = products[(products['category'] == target_category) & (products['numberOfReviews'] > 30)]
    filtered_products = filtered_products[filtered_products['_id'] != product_id]
    top_rated_products = filtered_products.sort_values('rate', ascending=False)
    top_10_rated_products = top_rated_products.head(10)
    return top_10_rated_products


#  kiểm tra xem item có phải là sản phẩm phổ biến hay không, nếu phải thì tính toán xem độ tương đồng là bn
#  x[1] là giá trị tương đồng chạy từ -1;1
#  danh sách recommend sẽ trả về các sp có độ tương đồng cao nhất từ trên xuống dưới , cho dù là sp phổ biến nhưng chưa chắc
#  tương đồng
#  có trường hợp chẳng đưa ra được recommend vì sp không có độ tương đồng
def recommedation_system(item):
    recommended_products_list = []
    if ObjectId(item) in pt.index:
        index = np.where(pt.index == ObjectId(item))[0][0]
        similarity_products = sorted(list(enumerate(similarity[index])), key=lambda x: x[1], reverse=True)[1:11]
        category_of_item = products.loc[products['_id'] == ObjectId(item), 'category'].values[0]
        for i in similarity_products:
            product_ID = pt.index[i[0]]
            if product_ID != ObjectId(item):
                product_info = products.loc[products['_id'] == product_ID]
                if len(product_info) > 0:
                    category_of_product = product_info['category'].values[0]
                    if category_of_product == category_of_item:
                        recommended_products_list.append({
                            "_id": str(product_info['_id'].values[0]),
                            # "category": product_info['category'].values[0],
                        })
    if len(recommended_products_list) < 10:
        top_rated_products = get_top_rated_products(ObjectId(item)).head(10 - len(recommended_products_list))
        top_rated_products_list = top_rated_products[['_id']].to_dict(orient='records')
        for product in top_rated_products_list:
            product["_id"] = str(product["_id"])
        recommended_products_list.extend(top_rated_products_list)
    if len(recommended_products_list) < 10:
        product_info = products.loc[products['_id'] == ObjectId(item)]
        if not product_info.empty:
            category = product_info['category'].values[0]
            category_product = products.loc[products['category'] == category]
            if len(category_product) > 1:
                category_product = category_product[category_product['_id'] != ObjectId(item)]
                category_product = category_product.head(10 - len(recommended_products_list))
                recommended_products_list = []
                for _, product in category_product.iterrows():
                    recommended_products_list.append({
                        "_id": str(product['_id']),
                        # "category": product['category']
                    })
    print(recommended_products_list)
    return recommended_products_list

app = Flask(__name__)

@app.route('/receive', methods=['POST', 'GET', 'PUT'])
def receive():
    if request.method == 'POST':
        data = request.json.get("obj_id")
        file_data = recommedation_system(data)
        return file_data

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
